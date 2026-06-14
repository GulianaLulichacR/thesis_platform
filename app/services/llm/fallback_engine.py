"""
FallbackEngine — Automatic free-provider fallback chain.

Behaviour:
  1. Try providers in LLM_PROVIDER_PRIORITY order.
  2. On LLMQuotaExceededError / LLMRateLimitError / LLMProviderUnavailableError
     → skip to next provider (transient, worth trying another).
  3. On LLMInvalidKeyError / LLMModelNotFoundError
     → skip to next provider (permanent config issue).
  4. On LLMTimeoutError → skip to next provider.
  5. If ALL providers fail → raise LLMAllProvidersFailedError.

Cache integration:
  - Check cache BEFORE any provider call.
  - Store successful responses in cache.

The engine respects the `use_fallback` flag on the request: if False,
only the request's specified provider is tried (no fallback).
"""

from app.core.config import get_settings
from app.core.exceptions import (
    LLMAllProvidersFailedError,
    LLMInvalidKeyError,
    LLMModelNotFoundError,
    LLMProviderError,
    LLMProviderUnavailableError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.core.logging import get_logger
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse, LLMProvider
from app.services.llm.cache import get_llm_cache

logger = get_logger(__name__)
settings = get_settings()

# Errors that mean "this provider can't serve the request right now — try next"
_FALLBACK_TRIGGER_ERRORS = (
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMProviderUnavailableError,
    LLMInvalidKeyError,
    LLMModelNotFoundError,
    LLMTimeoutError,
)


class FallbackEngine:
    """
    Orchestrates LLM calls across the configured free-provider chain.

    Import the singleton via `get_fallback_engine()`.
    """

    def __init__(self) -> None:
        self._settings = settings
        self._cache = get_llm_cache()

    async def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        """
        Generate a response, falling back through providers automatically.

        If `request.use_fallback` is False, only the requested provider is tried.
        """
        # ── Check cache first ────────────────────────────────────────────────
        cached = await self._cache.get(request)
        if cached is not None:
            logger.info(
                "LLM response served from cache",
                extra={"provider": cached.provider, "model": cached.model},
            )
            return cached

        # ── Build provider attempt list ───────────────────────────────────────
        if not request.use_fallback:
            # Respect explicit provider choice — no fallback
            providers_to_try = [request.provider.value]
        else:
            # Start with the requested provider, then the configured priority list
            priority = list(self._settings.LLM_PROVIDER_PRIORITY)
            requested = request.provider.value
            # Ensure requested provider is tried first
            if requested in priority:
                priority.remove(requested)
            providers_to_try = [requested] + priority

        # ── Attempt each provider in order ────────────────────────────────────
        provider_errors: dict[str, str] = {}

        for provider_name in providers_to_try:
            service = self._get_service(provider_name)
            if service is None:
                logger.debug(
                    "Skipping provider (not available/configured)",
                    extra={"provider": provider_name},
                )
                continue

            # Adapt the request to the actual provider being tried
            adapted = request.model_copy(
                update={
                    "provider": LLMProvider(provider_name),
                    "model": None,  # Let each service use its default_model
                }
            ) if provider_name != request.provider.value else request

            try:
                logger.info(
                    "Attempting LLM generation",
                    extra={"provider": provider_name, "attempt_order": list(providers_to_try)},
                )
                response = await service.generate(adapted)

                # Annotate whether a fallback provider was used
                if provider_name != request.provider.value:
                    response = response.model_copy(update={"used_fallback": True})
                    logger.warning(
                        "LLM fallback used",
                        extra={
                            "requested_provider": request.provider.value,
                            "actual_provider": provider_name,
                            "model": response.model,
                        },
                    )

                # ── Cache successful response ──────────────────────────────────
                await self._cache.set(request, response)
                return response

            except _FALLBACK_TRIGGER_ERRORS as exc:
                err_msg = str(exc)
                provider_errors[provider_name] = err_msg
                logger.warning(
                    "Provider failed — trying next",
                    extra={
                        "provider": provider_name,
                        "error_type": type(exc).__name__,
                        "error": err_msg,
                    },
                )
                continue  # Try next provider

            except LLMProviderError as exc:
                # Non-fallback-triggering error (e.g. generic 502)
                provider_errors[provider_name] = str(exc)
                logger.error(
                    "Provider error (non-retriable)",
                    extra={"provider": provider_name, "error": str(exc)},
                )
                if not request.use_fallback:
                    raise
                continue

        # ── All providers exhausted ───────────────────────────────────────────
        raise LLMAllProvidersFailedError(provider_errors)

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_service(provider_name: str):
        """
        Lazily instantiate the service for *provider_name*.
        Returns None if the provider is not configured / not enabled.
        """
        from app.services.llm.factory import LLMFactory
        try:
            return LLMFactory.create(provider_name)
        except Exception as exc:
            logger.debug(
                "Cannot instantiate provider (likely unconfigured)",
                extra={"provider": provider_name, "reason": str(exc)},
            )
            return None

    def cache_stats(self) -> dict:
        return self._cache.stats()


# ── Module-level singleton ─────────────────────────────────────────────────────

_engine: FallbackEngine | None = None


def get_fallback_engine() -> FallbackEngine:
    global _engine
    if _engine is None:
        _engine = FallbackEngine()
    return _engine
