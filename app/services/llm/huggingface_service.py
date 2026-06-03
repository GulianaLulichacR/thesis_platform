"""
HuggingFaceService — Free-tier HuggingFace Inference API integration.

Free tier details:
  - Inference API is FREE with an account (rate-limited without token)
  - With a free HF token: higher rate limits
  - Best free models for instruction following:
    * mistralai/Mistral-7B-Instruct-v0.3   (recommended, strong quality)
    * HuggingFaceH4/zephyr-7b-beta          (fast, good instruction following)
    * microsoft/Phi-3-mini-4k-instruct      (very small, CPU-friendly)
    * google/flan-t5-large                  (tiny, fast, moderate quality)

Notes:
  - Model loading can take 20-60s on first call (cold start)
  - Not all models support system prompts natively
"""

import httpx

from app.core.config import get_settings
from app.core.exceptions import (
    LLMModelNotFoundError,
    LLMProviderError,
    LLMProviderUnavailableError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.core.logging import get_logger
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse, LLMProvider
from app.services.llm.base import BaseLLMService

logger = get_logger(__name__)
settings = get_settings()

HF_INFERENCE_BASE = "https://api-inference.huggingface.co/models"


class HuggingFaceService(BaseLLMService):
    """
    HuggingFace Inference API provider (free tier).

    Uses the /models/{model} endpoint with the text-generation task.
    Supports optional HF API token for higher rate limits.
    """

    provider_name = "huggingface"
    default_model = "mistralai/Mistral-7B-Instruct-v0.3"
    provider_priority = 3      # Lowest priority — last resort free fallback

    def __init__(self) -> None:
        self._model = settings.HUGGINGFACE_MODEL or self.default_model
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.HUGGINGFACE_API_KEY:
            self._headers["Authorization"] = f"Bearer {settings.HUGGINGFACE_API_KEY}"
            logger.info("HuggingFaceService: authenticated with API token")
        else:
            logger.info(
                "HuggingFaceService: running WITHOUT API token (anonymous rate limits apply)"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────────────────

    async def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        model_name = self._resolve_model(request.model or self._model)
        url = f"{HF_INFERENCE_BASE}/{model_name}"

        # Build prompt with optional system prefix
        prompt = request.prompt
        if request.system_prompt:
            prompt = f"<s>[INST] <<SYS>>\n{request.system_prompt}\n<</SYS>>\n\n{request.prompt} [/INST]"

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": request.max_tokens,
                "temperature": max(request.temperature, 0.01),  # HF rejects temperature=0
                "return_full_text": False,
                "do_sample": True,
            },
            "options": {
                "wait_for_model": True,   # Wait instead of failing on cold start
                "use_cache": True,
            },
        }

        logger.debug(
            "HuggingFace generate request",
            extra={"model": model_name, "url": url},
        )

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
                resp = await client.post(url, json=payload, headers=self._headers)

            if resp.status_code == 200:
                data = resp.json()
                # Response is a list of dicts: [{"generated_text": "..."}]
                if isinstance(data, list) and data:
                    text = data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    text = data.get("generated_text", "")
                else:
                    text = str(data)

                logger.info(
                    "HuggingFace generation successful",
                    extra={"model": model_name, "chars": len(text)},
                )
                return LLMGenerateResponse(
                    text=text.strip(),
                    provider=LLMProvider.HUGGINGFACE,
                    model=model_name,
                    finish_reason="stop",
                )

            # ── Error handling by HTTP status ──────────────────────────────────

            body = self._safe_json(resp)
            error_msg = body.get("error", resp.text) if isinstance(body, dict) else resp.text

            if resp.status_code == 429:
                raise LLMRateLimitError("huggingface", error_msg)

            if resp.status_code == 503:
                # Usually "Model is currently loading" — treat as unavailable
                raise LLMProviderUnavailableError("huggingface", f"Model loading: {error_msg}")

            if resp.status_code == 404:
                raise LLMModelNotFoundError("huggingface", model_name)

            if resp.status_code in (401, 403):
                raise LLMRateLimitError(
                    "huggingface",
                    "Quota exceeded or token invalid. Check HUGGINGFACE_API_KEY.",
                )

            raise LLMProviderError("huggingface", f"HTTP {resp.status_code}: {error_msg}")

        except (LLMProviderError, LLMQuotaExceededError, LLMRateLimitError,
                LLMModelNotFoundError, LLMProviderUnavailableError):
            raise

        except httpx.TimeoutException:
            raise LLMTimeoutError("huggingface", settings.LLM_REQUEST_TIMEOUT)

        except httpx.ConnectError as exc:
            raise LLMProviderUnavailableError(
                "huggingface", f"Cannot reach HuggingFace API: {exc}"
            ) from exc

        except Exception as exc:
            logger.exception("HuggingFace unexpected error")
            raise LLMProviderError("huggingface", str(exc)) from exc

    async def health_check(self) -> bool:
        """Ping the model metadata endpoint — no generation cost."""
        url = f"https://huggingface.co/api/models/{self._model}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("HuggingFace health check error", extra={"error": str(exc)})
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_json(resp: httpx.Response) -> dict | list | None:
        try:
            return resp.json()
        except Exception:
            return None
