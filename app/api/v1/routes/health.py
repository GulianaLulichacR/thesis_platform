"""
AI Health Check routes — GET /api/v1/health/ai

Returns:
  - Per-provider status (healthy / unhealthy / disabled)
  - Overall AI stack status
  - Cache statistics
  - Recommended active provider
  - Ollama model list (if healthy)
"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.cache import get_llm_cache
from app.services.llm.factory import LLMFactory

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)
settings = get_settings()


async def _check_provider(provider_name: str) -> dict:
    """Run health_check() for a single provider and return a status dict."""
    try:
        service = LLMFactory.create(provider_name)
        healthy = await service.health_check()

        extra: dict = {}
        # Attach Ollama model list when healthy
        if provider_name == "ollama" and healthy:
            from app.services.llm.ollama_service import OllamaService
            ollama_models = await service.list_models()  # type: ignore[attr-defined]
            extra["available_models"] = ollama_models

        return {
            "provider": provider_name,
            "status": "healthy" if healthy else "unhealthy",
            "enabled": True,
            **extra,
        }
    except Exception as exc:
        return {
            "provider": provider_name,
            "status": "error",
            "enabled": True,
            "error": str(exc),
        }


@router.get(
    "/ai",
    summary="AI provider health check",
    description=(
        "Concurrently checks all enabled free AI providers "
        "(Gemini, Ollama, HuggingFace) and returns their health status."
    ),
)
async def ai_health() -> JSONResponse:
    """
    Concurrent health check for all configured free-tier LLM providers.

    Response codes:
      200 — at least one provider is healthy
      503 — all providers are down
    """
    checks: list[dict] = []

    # Build tasks only for enabled providers
    provider_tasks: dict[str, asyncio.Task] = {}

    async def run_check(name: str) -> dict:
        return await _check_provider(name)

    tasks = {
        name: asyncio.create_task(run_check(name))
        for name in LLMFactory.available_providers()
    }

    # Also mark disabled providers without calling them
    all_names = {"gemini", "ollama", "huggingface"}
    enabled_names = set(LLMFactory.available_providers())
    disabled_names = all_names - enabled_names

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            checks.append({"provider": name, "status": "error", "enabled": True, "error": str(result)})
        else:
            checks.append(result)

    for name in disabled_names:
        checks.append({"provider": name, "status": "disabled", "enabled": False})

    # Determine overall status
    healthy_providers = [c["provider"] for c in checks if c.get("status") == "healthy"]
    overall = "healthy" if healthy_providers else "degraded"

    # Recommend the highest-priority healthy provider
    priority = settings.LLM_PROVIDER_PRIORITY
    recommended = next(
        (p for p in priority if p in healthy_providers),
        healthy_providers[0] if healthy_providers else None,
    )

    # Cache statistics
    cache_stats = get_llm_cache().stats()

    response_data = {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recommended_provider": recommended,
        "providers": checks,
        "provider_priority": settings.LLM_PROVIDER_PRIORITY,
        "cache": cache_stats,
        "free_tier_tips": {
            "gemini": "Free: 15 RPM, 1M tokens/day on gemini-1.5-flash",
            "ollama": "Free: unlimited (local inference), RAM-bound",
            "huggingface": "Free: limited RPM, higher with HF token",
        },
    }

    status_code = status.HTTP_200_OK if healthy_providers else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=response_data, status_code=status_code)


@router.get(
    "/ai/cache",
    summary="LLM response cache statistics",
)
async def cache_stats() -> dict:
    """Return current LLM response cache statistics."""
    return get_llm_cache().stats()


@router.get(
    "/ai/providers",
    summary="List all registered LLM providers",
)
async def list_providers() -> dict:
    """List all registered free-tier providers and their enabled state."""
    return {
        "available": LLMFactory.available_providers(),
        "enabled": LLMFactory.enabled_providers(),
        "priority_order": settings.LLM_PROVIDER_PRIORITY,
        "default_provider": settings.DEFAULT_LLM_PROVIDER,
        "default_model": settings.DEFAULT_LLM_MODEL,
    }
