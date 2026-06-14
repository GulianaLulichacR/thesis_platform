import re
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import (
    LLMProviderError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.core.logging import get_logger
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse, LLMProvider
from app.services.llm.base import BaseLLMService

logger = get_logger(__name__)
settings = get_settings()

_VALID_MODEL_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9:.\-]{0,99}$")


def _sanitize_base_url(raw: str) -> str:
    """
    Normalise the Ollama base URL so that path joins never produce double
    slashes and the scheme is always present.
    """
    url = raw.strip()
    if not url:
        raise LLMProviderError("ollama", "OLLAMA_BASE_URL is empty.")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _build_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


class OllamaService(BaseLLMService):
    """
    LLM provider backed by a local (or remote) Ollama instance.
    """

    provider_name = "ollama"
    provider_priority = 2   # Second in free chain (after Gemini)

    @property
    def default_model(self) -> str:  # type: ignore[override]
        return settings.OLLAMA_MODEL

    def __init__(self) -> None:
        if not settings.OLLAMA_ENABLED:
            raise LLMProviderError("ollama", "Ollama is disabled (OLLAMA_ENABLED=false).")
        self._base_url = _sanitize_base_url(settings.OLLAMA_BASE_URL)
        logger.debug("OllamaService initialised", extra={"base_url": self._base_url})

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _resolve_model(self, model: str | None) -> str:  # type: ignore[override]
        if model and _VALID_MODEL_RE.match(model.strip()):
            return model.strip()
        logger.warning(
            "Ollama: invalid or missing model name — falling back to default",
            extra={"requested": model, "fallback": self.default_model},
        )
        return self.default_model

    @staticmethod
    def _extract_ollama_error(response: httpx.Response) -> str:
        try:
            body = response.json()
            return body.get("error") or body.get("message") or str(body)
        except Exception:
            return response.text or f"HTTP {response.status_code}"

    # ──────────────────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────────────────

    async def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        model_name = self._resolve_model(request.model)
        endpoint = _build_url(self._base_url, "/api/generate")

        prompt = request.prompt
        if request.system_prompt:
            prompt = f"[SYSTEM]\n{request.system_prompt}\n\n[USER]\n{prompt}"

        payload: dict = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        logger.debug(
            "Ollama generate request",
            extra={"endpoint": endpoint, "model": model_name},
        )

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
                resp = await client.post(endpoint, json=payload)

            if resp.is_error:
                ollama_message = self._extract_ollama_error(resp)
                logger.error(
                    "Ollama returned an error response",
                    extra={
                        "status_code": resp.status_code,
                        "endpoint": endpoint,
                        "model": model_name,
                        "ollama_error": ollama_message,
                    },
                )
                raise LLMProviderError(
                    "ollama",
                    f"HTTP {resp.status_code} from {endpoint} — {ollama_message}",
                )

            data = resp.json()

        except LLMProviderError:
            raise

        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("ollama", settings.LLM_REQUEST_TIMEOUT) from exc

        except httpx.ConnectError as exc:
            raise LLMProviderUnavailableError(
                "ollama",
                f"Cannot connect to Ollama at {self._base_url}. "
                "Is Ollama running and OLLAMA_BASE_URL correct?",
            ) from exc

        except Exception as exc:
            logger.exception("Unexpected error during Ollama generate")
            raise LLMProviderError("ollama", str(exc)) from exc

        return LLMGenerateResponse(
            text=data.get("response", ""),
            provider=LLMProvider.OLLAMA,
            model=model_name,
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            finish_reason="stop" if data.get("done") else None,
        )

    async def health_check(self) -> bool:
        """Ping /api/tags — a 200 means Ollama is up and has at least one model."""
        endpoint = _build_url(self._base_url, "/api/tags")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(endpoint)
            healthy = resp.status_code == 200
            if not healthy:
                logger.warning(
                    "Ollama health check failed",
                    extra={"status_code": resp.status_code},
                )
            return healthy
        except Exception as exc:
            logger.warning("Ollama health check error", extra={"error": str(exc)})
            return False

    async def list_models(self) -> list[str]:
        """Return the names of all locally pulled Ollama models."""
        endpoint = _build_url(self._base_url, "/api/tags")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(endpoint)
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []