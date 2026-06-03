"""
GeminiService — Production-grade FREE Gemini integration.

Features:
  - Uses google-generativeai SDK (latest)
  - Supports gemini-1.5-flash and gemini-2.0-flash-exp (both free tier)
  - Exponential backoff retry on transient errors
  - Granular quota / rate-limit / key / model-not-found detection
  - Truly async via asyncio.to_thread (SDK is sync-only)
  - Reports token usage from usage_metadata
  - Lightweight health check using count_tokens
"""

import asyncio
import math
import re
import time

import google.generativeai as genai

from app.core.config import get_settings
from app.core.exceptions import (
    LLMInvalidKeyError,
    LLMModelNotFoundError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.core.logging import get_logger
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse, LLMProvider
from app.services.llm.base import BaseLLMService

logger = get_logger(__name__)
settings = get_settings()

# Patterns that indicate specific quota / rate-limit conditions from Gemini errors
_QUOTA_PATTERNS = [
    r"quota",
    r"resource_exhausted",
    r"RESOURCE_EXHAUSTED",
    r"ratequotaexceeded",
    r"userRateLimitExceeded",
    r"429",
]
_RATE_LIMIT_PATTERNS = [
    r"rate.?limit",
    r"per.*minute",
    r"per.*second",
    r"RATE_LIMIT_EXCEEDED",
]
_KEY_PATTERNS = [
    r"api.?key",
    r"invalid.?key",
    r"permission.?denied",
    r"PERMISSION_DENIED",
    r"unauthenticated",
    r"UNAUTHENTICATED",
    r"401",
    r"403",
]
_MODEL_PATTERNS = [
    r"model.*not.*found",
    r"not.*found.*model",
    r"invalid.?model",
    r"MODEL_NOT_FOUND",
    r"404",
]


def _classify_gemini_error(exc: Exception, provider: str, model: str) -> LLMProviderError:
    """Inspect the exception message and return the most specific subclass."""
    msg = str(exc).lower()

    for pat in _MODEL_PATTERNS:
        if re.search(pat, msg, re.IGNORECASE):
            return LLMModelNotFoundError(provider, model)

    for pat in _KEY_PATTERNS:
        if re.search(pat, msg, re.IGNORECASE):
            return LLMInvalidKeyError(provider, str(exc))

    for pat in _QUOTA_PATTERNS:
        if re.search(pat, msg, re.IGNORECASE):
            return LLMQuotaExceededError(provider, str(exc))

    for pat in _RATE_LIMIT_PATTERNS:
        if re.search(pat, msg, re.IGNORECASE):
            return LLMRateLimitError(provider, str(exc))

    return LLMProviderError(provider, str(exc))


class GeminiService(BaseLLMService):
    """
    Google Gemini (free tier) provider.

    Recommended free models:
      - gemini-1.5-flash    — fast, good quality, generous free quota
      - gemini-1.5-flash-8b — smallest, lowest latency, most free RPM
      - gemini-2.0-flash-exp — experimental, very capable, free while in preview
    """

    provider_name = "gemini"
    default_model = "gemini-1.5-flash"
    provider_priority = 1          # Highest priority in fallback chain
    supports_embeddings = True     # Gemini text-embedding-004 available

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise LLMInvalidKeyError("gemini", "GEMINI_API_KEY is not configured.")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        logger.info(
            "GeminiService initialised",
            extra={"default_model": self.default_model, "env_model": settings.GEMINI_MODEL},
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────────────────

    async def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        model_name = self._resolve_model(request.model or settings.GEMINI_MODEL)
        max_retries = settings.LLM_MAX_RETRIES
        base_delay = settings.LLM_RETRY_BASE_DELAY
        max_delay = settings.LLM_RETRY_MAX_DELAY

        last_exc: LLMProviderError | None = None

        for attempt in range(1, max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._call_gemini_sync,
                        model_name,
                        request.prompt,
                        request.system_prompt,
                        request.temperature,
                        request.max_tokens,
                    ),
                    timeout=settings.LLM_REQUEST_TIMEOUT,
                )

                logger.info(
                    "Gemini generation successful",
                    extra={
                        "model": model_name,
                        "attempt": attempt,
                        "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else None,
                        "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else None,
                    },
                )

                return LLMGenerateResponse(
                    text=response.text,
                    provider=LLMProvider.GEMINI,
                    model=model_name,
                    input_tokens=getattr(response.usage_metadata, "prompt_token_count", None),
                    output_tokens=getattr(response.usage_metadata, "candidates_token_count", None),
                    finish_reason=self._finish_reason(response),
                )

            except asyncio.TimeoutError as exc:
                last_exc = LLMTimeoutError("gemini", settings.LLM_REQUEST_TIMEOUT)
                logger.warning(
                    "Gemini timeout",
                    extra={"attempt": attempt, "timeout": settings.LLM_REQUEST_TIMEOUT},
                )

            except LLMProviderError:
                # Already classified — re-raise immediately (no retry on auth/quota)
                raise

            except Exception as exc:
                classified = _classify_gemini_error(exc, "gemini", model_name)

                # Quota/key errors: no point retrying, fail fast for fallback chain
                if isinstance(classified, (LLMQuotaExceededError, LLMInvalidKeyError, LLMModelNotFoundError)):
                    logger.warning(
                        "Gemini permanent error — skipping retries",
                        extra={"type": type(classified).__name__, "model": model_name},
                    )
                    raise classified from exc

                last_exc = classified
                logger.warning(
                    "Gemini transient error",
                    extra={"attempt": attempt, "max_retries": max_retries, "error": str(exc)},
                )

            # Exponential backoff before next retry
            if attempt < max_retries:
                delay = min(base_delay * math.pow(2, attempt - 1), max_delay)
                logger.debug("Gemini retry backoff", extra={"delay_seconds": delay, "next_attempt": attempt + 1})
                await asyncio.sleep(delay)

        # All retries exhausted
        raise last_exc or LLMProviderError("gemini", "All retries exhausted")

    async def health_check(self) -> bool:
        """
        Lightweight check using count_tokens (does NOT consume generation quota).
        """
        try:
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            # count_tokens is sync but very cheap — no generation cost
            await asyncio.to_thread(model.count_tokens, "health")
            return True
        except Exception as exc:
            logger.warning("Gemini health check failed", extra={"error": str(exc)})
            return False

    async def embed(self, text: str) -> list[float]:
        """Embed text using Gemini text-embedding-004 (free tier)."""
        try:
            result = await asyncio.to_thread(
                genai.embed_content,
                model="models/text-embedding-004",
                content=text,
            )
            return result["embedding"]
        except Exception as exc:
            raise LLMProviderError("gemini", f"Embedding failed: {exc}") from exc

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _call_gemini_sync(
        model_name: str,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ):
        """Synchronous Gemini SDK call — run inside asyncio.to_thread."""
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        model_kwargs: dict = {"model_name": model_name, "generation_config": generation_config}
        if system_prompt:
            model_kwargs["system_instruction"] = system_prompt

        model = genai.GenerativeModel(**model_kwargs)
        return model.generate_content(prompt)

    @staticmethod
    def _finish_reason(response) -> str | None:
        """Extract finish_reason string from Gemini response."""
        try:
            candidate = response.candidates[0]
            return candidate.finish_reason.name if candidate.finish_reason else None
        except (IndexError, AttributeError):
            return None