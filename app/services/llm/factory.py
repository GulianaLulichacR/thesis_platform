"""
LLM Provider Factory — FREE providers only.

Registered providers (in priority order):
  1. Gemini   (Google free tier)
  2. Ollama   (local, free)
  3. HuggingFace (free inference API)

REMOVED: OpenAI, Anthropic/Claude (paid services).
"""

from app.core.config import get_settings
from app.core.exceptions import LLMProviderNotFoundError
from app.schemas.llm import LLMProvider
from app.services.llm.base import BaseLLMService

settings = get_settings()


class LLMFactory:
    """
    Registry + factory for LLM provider instances.

    Providers are instantiated lazily (on first `.create()` call).
    Instantiation can fail if the provider is not configured — callers should
    handle `LLMProviderError` / `LLMInvalidKeyError` gracefully.
    """

    _registry: dict[str, type[BaseLLMService]] = {}

    @classmethod
    def register(cls, provider: LLMProvider | str, service_cls: type[BaseLLMService]) -> None:
        key = provider.value if isinstance(provider, LLMProvider) else provider
        cls._registry[key] = service_cls

    @classmethod
    def create(cls, provider: LLMProvider | str) -> BaseLLMService:
        key = provider.value if isinstance(provider, LLMProvider) else provider
        service_cls = cls._registry.get(key)
        if service_cls is None:
            raise LLMProviderNotFoundError(key)
        return service_cls()

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def enabled_providers(cls) -> list[str]:
        """
        Returns providers that are both registered AND have their config enabled.
        Useful for health checks and observability.
        """
        enabled = []
        for name in cls._registry:
            if name == "gemini" and settings.GEMINI_ENABLED:
                enabled.append(name)
            elif name == "ollama" and settings.OLLAMA_ENABLED:
                enabled.append(name)
            elif name == "huggingface" and settings.HUGGINGFACE_ENABLED:
                enabled.append(name)
        return enabled


def _register_all() -> None:
    """Register all FREE provider implementations."""
    from app.services.llm.gemini_service import GeminiService
    from app.services.llm.huggingface_service import HuggingFaceService
    from app.services.llm.ollama_service import OllamaService

    LLMFactory.register(LLMProvider.GEMINI, GeminiService)
    LLMFactory.register(LLMProvider.OLLAMA, OllamaService)
    LLMFactory.register(LLMProvider.HUGGINGFACE, HuggingFaceService)


_register_all()


# ── FastAPI dependencies ───────────────────────────────────────────────────────

def get_llm_service(provider: str) -> BaseLLMService:
    """FastAPI dependency: return a single provider instance by name."""
    return LLMFactory.create(provider)


def get_fallback_engine():
    """FastAPI dependency: return the global FallbackEngine instance."""
    from app.services.llm.fallback_engine import get_fallback_engine as _get
    return _get()
