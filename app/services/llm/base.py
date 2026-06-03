from abc import ABC, abstractmethod
from typing import Any

from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse


class BaseLLMService(ABC):
    """
    Abstract base for all LLM provider implementations.

    Every provider must implement `generate`, `health_check`, and expose
    `provider_name` and `default_model` class attributes.

    Future-proof hooks for RAG and embeddings are provided as optional stubs.
    """

    # ── Required class-level metadata ─────────────────────────────────────────

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier (e.g. 'gemini', 'ollama')."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Model used when none is specified in the request."""
        ...

    # ── Priority for fallback ordering (lower = higher priority) ──────────────

    provider_priority: int = 99  # Override per provider; lower = tried first

    # ── Capability flags ──────────────────────────────────────────────────────

    supports_streaming: bool = False   # Set True when streaming is implemented
    supports_embeddings: bool = False  # Set True when embed() is implemented

    # ── Core interface ────────────────────────────────────────────────────────

    @abstractmethod
    async def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        """Generate a text completion for the given request."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and functional."""
        ...

    # ── Optional future-proof hooks (RAG / embeddings) ────────────────────────

    async def embed(self, text: str) -> list[float]:
        """
        Return a vector embedding for *text*.

        Raises NotImplementedError by default.  Override in providers that
        support embeddings (Gemini text-embedding-004, Ollama nomic-embed-text).
        """
        raise NotImplementedError(
            f"Provider '{self.provider_name}' does not support embeddings yet."
        )

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _resolve_model(self, model: str | None) -> str:
        return model or self.default_model

    def _build_messages(
        self, prompt: str, system_prompt: str | None = None
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages
