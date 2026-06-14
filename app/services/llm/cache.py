"""
LLM Response Cache — In-memory LRU cache with TTL.

Keyed on (provider, model, prompt_hash) — identical prompts return the cached
response without hitting the API, saving free-tier quota.

Thread-safe: uses asyncio.Lock for async access.
Cache is intentionally shared across all requests (module-level singleton).
"""

import asyncio
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class _CacheEntry:
    response: LLMGenerateResponse
    expires_at: float


class LLMResponseCache:
    """
    Thread-safe async LRU cache for LLM responses.

    Usage:
        cache = get_llm_cache()
        hit = await cache.get(request)
        if hit:
            return hit
        response = await provider.generate(request)
        await cache.set(request, response)
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 300) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    # ── Public interface ───────────────────────────────────────────────────────

    async def get(self, request: LLMGenerateRequest) -> LLMGenerateResponse | None:
        if not settings.LLM_CACHE_ENABLED:
            return None

        key = self._make_key(request)
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.monotonic() > entry.expires_at:
                # TTL expired — evict
                del self._store[key]
                self._misses += 1
                return None
            # LRU: move to end (most recently used)
            self._store.move_to_end(key)
            self._hits += 1
            logger.debug("LLM cache HIT", extra={"key_prefix": key[:32]})
            # Return a copy flagged as cache_hit
            cached = entry.response.model_copy(update={"cache_hit": True})
            return cached

    async def set(self, request: LLMGenerateRequest, response: LLMGenerateResponse) -> None:
        if not settings.LLM_CACHE_ENABLED:
            return

        key = self._make_key(request)
        async with self._lock:
            # Evict oldest entry if at capacity
            if len(self._store) >= self._max_size and key not in self._store:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]

            self._store[key] = _CacheEntry(
                response=response,
                expires_at=time.monotonic() + self._ttl,
            )
            self._store.move_to_end(key)
            logger.debug("LLM cache SET", extra={"key_prefix": key[:32], "size": len(self._store)})

    async def invalidate(self, request: LLMGenerateRequest) -> None:
        key = self._make_key(request)
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
            logger.info("LLM cache cleared")

    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total else 0.0,
            "size": len(self._store),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "enabled": settings.LLM_CACHE_ENABLED,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_key(request: LLMGenerateRequest) -> str:
        """
        Deterministic cache key from (provider, model, system_prompt, prompt, temperature).
        Different temperatures → different generations, so temperature is included.
        """
        raw = "|".join([
            request.provider.value,
            request.model or "",
            request.system_prompt or "",
            request.prompt,
            str(round(request.temperature, 2)),
        ])
        return hashlib.sha256(raw.encode()).hexdigest()


# ── Module-level singleton ─────────────────────────────────────────────────────

_cache: LLMResponseCache | None = None


def get_llm_cache() -> LLMResponseCache:
    global _cache
    if _cache is None:
        _cache = LLMResponseCache(
            max_size=settings.LLM_CACHE_MAX_SIZE,
            ttl_seconds=settings.LLM_CACHE_TTL_SECONDS,
        )
        logger.info(
            "LLM response cache initialised",
            extra={
                "max_size": settings.LLM_CACHE_MAX_SIZE,
                "ttl_seconds": settings.LLM_CACHE_TTL_SECONDS,
                "enabled": settings.LLM_CACHE_ENABLED,
            },
        )
    return _cache
