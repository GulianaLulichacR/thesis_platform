from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Base Exception ───────────────────────────────────────────────────────────

class ThesisPlatformError(Exception):
    """Base exception for all platform errors."""
    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ─── Document Exceptions ──────────────────────────────────────────────────────

class DocumentLoadError(ThesisPlatformError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


class UnsupportedFileTypeError(ThesisPlatformError):
    def __init__(self, ext: str) -> None:
        super().__init__(
            f"File type '{ext}' is not supported.",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


# ─── LLM Exceptions (granular) ────────────────────────────────────────────────

class LLMProviderError(ThesisPlatformError):
    """Generic LLM provider error — use subclasses for specific conditions."""
    def __init__(self, provider: str, detail: str) -> None:
        self.provider = provider
        super().__init__(
            f"LLM provider '{provider}' error: {detail}",
            status.HTTP_502_BAD_GATEWAY,
        )


class LLMQuotaExceededError(LLMProviderError):
    """Free-tier quota exhausted — triggers automatic fallback to next provider."""
    def __init__(self, provider: str, detail: str = "Free-tier quota exceeded") -> None:
        super().__init__(provider, detail)
        self.status_code = status.HTTP_429_TOO_MANY_REQUESTS


class LLMRateLimitError(LLMProviderError):
    """Per-minute / per-day rate limit hit — triggers backoff + retry."""
    def __init__(self, provider: str, detail: str = "Rate limit exceeded") -> None:
        super().__init__(provider, detail)
        self.status_code = status.HTTP_429_TOO_MANY_REQUESTS


class LLMInvalidKeyError(LLMProviderError):
    """API key is missing, invalid, or revoked."""
    def __init__(self, provider: str, detail: str = "Invalid or missing API key") -> None:
        super().__init__(provider, detail)
        self.status_code = status.HTTP_401_UNAUTHORIZED


class LLMModelNotFoundError(LLMProviderError):
    """Requested model does not exist or is not available in free tier."""
    def __init__(self, provider: str, model: str) -> None:
        super().__init__(provider, f"Model '{model}' not found or not available")
        self.status_code = status.HTTP_404_NOT_FOUND


class LLMTimeoutError(LLMProviderError):
    """Provider did not respond within the configured timeout."""
    def __init__(self, provider: str, timeout: float) -> None:
        super().__init__(provider, f"Request timed out after {timeout}s")
        self.status_code = status.HTTP_504_GATEWAY_TIMEOUT


class LLMProviderUnavailableError(LLMProviderError):
    """Provider is unreachable (no connection, service down, etc.)."""
    def __init__(self, provider: str, detail: str = "Provider unreachable") -> None:
        super().__init__(provider, detail)
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class LLMAllProvidersFailedError(ThesisPlatformError):
    """All configured free providers failed — no fallback left."""
    def __init__(self, errors: dict[str, str]) -> None:
        detail = "; ".join(f"{p}: {e}" for p, e in errors.items())
        super().__init__(
            f"All LLM providers failed: {detail}",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.provider_errors = errors


class LLMProviderNotFoundError(ThesisPlatformError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            f"LLM provider '{provider}' not found.",
            status.HTTP_400_BAD_REQUEST,
        )


# ─── Analysis / Storage Exceptions ───────────────────────────────────────────

class AnalysisError(ThesisPlatformError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class StorageError(ThesisPlatformError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─── Exception Handlers ───────────────────────────────────────────────────────

async def platform_exception_handler(request: Request, exc: ThesisPlatformError) -> JSONResponse:
    logger.error(
        "Platform error",
        extra={"path": str(request.url), "error": exc.message, "type": type(exc).__name__},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "type": type(exc).__name__},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "type": "HTTPException"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation failed", "details": errors, "type": "ValidationError"},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", extra={"path": str(request.url)})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An unexpected error occurred.", "type": "InternalServerError"},
    )
