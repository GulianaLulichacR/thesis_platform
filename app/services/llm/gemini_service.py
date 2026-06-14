# pyright: reportPrivateImportUsage=none
"""
GeminiService — Production-grade FREE Gemini integration (New google-genai SDK).
"""

import asyncio
import math
import re

from google import genai
from google.genai import types

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

_QUOTA_PATTERNS = [
    r"quota", r"resource_exhausted", r"RESOURCE_EXHAUSTED",
    r"ratequotaexceeded", r"userRateLimitExceeded", r"429",
]
_RATE_LIMIT_PATTERNS = [
    r"rate.?limit", r"per.*minute", r"per.*second", r"RATE_LIMIT_EXCEEDED",
]
_KEY_PATTERNS = [
    r"api.?key", r"invalid.?key", r"permission.?denied", r"PERMISSION_DENIED",
    r"unauthenticated", r"UNAUTHENTICATED", r"401", r"403",
]
_MODEL_PATTERNS = [
    r"model.*not.*found", r"not.*found.*model", r"invalid.?model",
    r"MODEL_NOT_FOUND", r"404",
]


def _classify_gemini_error(exc: Exception, provider: str, model: str) -> LLMProviderError:
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
    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-1.5-flash"

    @property
    def provider_priority(self) -> int:
        return 1

    @property
    def supports_embeddings(self) -> bool:
        return True

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise LLMInvalidKeyError("gemini", "GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info(
            "GeminiService initialised",
            extra={"default_model": self.default_model, "env_model": settings.GEMINI_MODEL},
        )

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
                        self.client,
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
                    text=response.text or "",
                    provider=LLMProvider.GEMINI,
                    model=model_name,
                    input_tokens=getattr(response.usage_metadata, "prompt_token_count", None),
                    output_tokens=getattr(response.usage_metadata, "candidates_token_count", None),
                    finish_reason=self._finish_reason(response) or "unknown",
                )
            except asyncio.TimeoutError as exc:
                last_exc = LLMTimeoutError("gemini", settings.LLM_REQUEST_TIMEOUT)
                logger.warning("Gemini timeout", extra={"attempt": attempt, "timeout": settings.LLM_REQUEST_TIMEOUT})
            except LLMProviderError:
                raise
            except Exception as exc:
                classified = _classify_gemini_error(exc, "gemini", model_name)
                if isinstance(classified, (LLMQuotaExceededError, LLMInvalidKeyError, LLMModelNotFoundError)):
                    logger.warning("Gemini permanent error — skipping retries", extra={"type": type(classified).__name__, "model": model_name})
                    raise classified from exc
                last_exc = classified
                logger.warning("Gemini transient error", extra={"attempt": attempt, "max_retries": max_retries, "error": str(exc)})
            if attempt < max_retries:
                delay = min(base_delay * math.pow(2, attempt - 1), max_delay)
                logger.debug("Gemini retry backoff", extra={"delay_seconds": delay, "next_attempt": attempt + 1})
                await asyncio.sleep(delay)
        raise last_exc or LLMProviderError("gemini", "All retries exhausted")

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(
                self.client.models.count_tokens,
                model=settings.GEMINI_MODEL,
                contents="health",
            )
            return True
        except Exception as exc:
            logger.warning("Gemini health check failed", extra={"error": str(exc)})
            return False

    async def embed(self, text: str) -> list[float]:
        """Embed text using Gemini text-embedding-004."""
        try:
            result = await asyncio.to_thread(
                self.client.models.embed_content,
                model="text-embedding-004",
                contents=text,
            )
            
            # Validaciones para satisfacer a Pylance y evitar crashes en runtime
            if not result.embeddings:
                raise ValueError("Gemini returned empty embeddings.")
                
            embedding_values = result.embeddings[0].values
            if embedding_values is None:
                raise ValueError("Gemini embedding values are None.")
                
            return embedding_values
            
        except Exception as exc:
            raise LLMProviderError("gemini", f"Embedding failed: {exc}") from exc

    @staticmethod
    def _call_gemini_sync(
        client: genai.Client,
        model_name: str,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ):
        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        config = types.GenerateContentConfig(**config_kwargs)
        return client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

    @staticmethod
    def _finish_reason(response) -> str | None:
        try:
            candidate = response.candidates[0]
            fr = candidate.finish_reason
            return str(fr) if fr else None
        except (IndexError, AttributeError):
            return None