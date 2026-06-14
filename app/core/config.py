from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    VECTOR_DB_DIR: str = "vector_db"

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Thesis Review AI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # ─── Server ───────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # ─── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ─── Paths ────────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATA_DIR: Path = BASE_DIR / "data"
    VECTOR_DB_PATH: Path = BASE_DIR / "vector_db"

    # ─── Gemini (FREE TIER) ───────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-1.5-flash-8b"  # Smaller/cheaper fallback
    GEMINI_ENABLED: bool = False

    # ─── Ollama (LOCAL / FREE) ────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_ENABLED: bool = True

    # ─── HuggingFace (FREE TIER) ──────────────────────────────────────────────
    HUGGINGFACE_API_KEY: str = ""  # Optional: free tier works without key (rate-limited)
    HUGGINGFACE_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.3"
    HUGGINGFACE_ENABLED: bool = False  # Enable explicitly when key is set

    # ─── Provider Priority (fallback chain order) ─────────────────────────────
    # First available provider in this list is used; falls back on quota/error
    LLM_PROVIDER_PRIORITY: list[str] = ["gemini", "ollama", "huggingface"]

    # ─── Default LLM (used when provider not specified) ───────────────────────
    DEFAULT_LLM_PROVIDER: str = "gemini"
    DEFAULT_LLM_MODEL: str = "gemini-1.5-flash"

    # ─── AI Detection (free/freemium with safe fallback) ──────────────────────
    AI_DETECTION_PROVIDER: str = "mock"
    GPTZERO_API_KEY: str = ""
    WINSTON_API_KEY: str = ""
    ORIGINALITY_API_KEY: str = ""

    # ─── Streamlit frontend ────────────────────────────────────────────────────
    STREAMLIT_BACKEND_URL: str = "http://localhost:8000"

    # ─── Retry / Backoff ──────────────────────────────────────────────────────
    LLM_MAX_RETRIES: int = 3               # Max retries per provider
    LLM_RETRY_BASE_DELAY: float = 1.0      # Base delay in seconds (exponential backoff)
    LLM_RETRY_MAX_DELAY: float = 30.0      # Cap for backoff delay
    LLM_REQUEST_TIMEOUT: float = 120.0     # Provider request timeout (seconds)

    # ─── Response Cache ───────────────────────────────────────────────────────
    LLM_CACHE_ENABLED: bool = True
    LLM_CACHE_TTL_SECONDS: int = 300       # 5 minutes
    LLM_CACHE_MAX_SIZE: int = 256          # Max cached entries (LRU eviction)

    # ─── File Upload ──────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: set[str] = {"pdf", "docx"}

    # ─── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @field_validator("LLM_PROVIDER_PRIORITY", mode="before")
    @classmethod
    def parse_provider_priority(cls, v: str | list) -> list[str]:
        """Allow comma-separated string from env var."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        for d in (self.UPLOAD_DIR, self.DATA_DIR, self.VECTOR_DB_PATH):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_ENABLED)

    @property
    def huggingface_configured(self) -> bool:
        return bool(self.HUGGINGFACE_ENABLED)


@lru_cache
def get_settings() -> Settings:
    return Settings()
