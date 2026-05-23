"""
Optional Redis-backed cache for NER / language / domain hints.

Disabled unless ``ENABLE_CACHING=true``. If Redis is unavailable or the
``redis`` package is missing, all operations fail soft (return ``None``).
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Callable, TypeVar

from config.settings import get_settings

T = TypeVar("T")

_log = logging.getLogger(__name__)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="surrogateescape")).hexdigest()


class CacheService:
    """Thin wrapper with graceful degradation."""

    def __init__(self) -> None:
        self._client: Any = None
        self._redis_module = None
        self._connect()

    def _connect(self) -> None:
        settings = get_settings()
        if not settings.enable_caching:
            return
        try:
            import redis  # type: ignore
        except ImportError:
            _log.warning("ENABLE_CACHING is true but redis is not installed; caching disabled")
            return
        self._redis_module = redis
        try:
            self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1.0)
            self._client.ping()
        except Exception as e:
            _log.warning("Redis connection failed (%s); caching disabled", e)
            self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def get_json(self, key: str) -> Any | None:
        if not self._client:
            return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            _log.debug("cache get failed for %s: %s", key, e)
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        if not self._client:
            return False
        try:
            payload = json.dumps(value, ensure_ascii=False)
            return bool(self._client.setex(key, ttl_seconds, payload))
        except Exception as e:
            _log.debug("cache set failed for %s: %s", key, e)
            return False

    def delete(self, key: str) -> None:
        if not self._client:
            return
        try:
            self._client.delete(key)
        except Exception:
            pass

    # --- Key helpers ---

    def ner_key(self, text: str, domain: str) -> str:
        h = _sha256_text(f"{domain}:{text}")
        return f"lexscan:ner:{h}"

    def lang_key(self, text: str) -> str:
        h = _sha256_text(text[:8000])
        return f"lexscan:lang:{h}"

    def domain_key(self, text: str) -> str:
        h = _sha256_text(text[:8000])
        return f"lexscan:domain:{h}"

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl_seconds: int,
    ) -> T:
        """
        Return cached JSON-deserialized value, or compute and store.

        Note: ``factory`` return value must be JSON-serializable for storage.
        If caching is off or fails, always returns ``factory()`` result.
        """
        cached = self.get_json(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        value = factory()
        self.set_json(key, value, ttl_seconds)
        return value


_singleton: CacheService | None = None


def get_cache() -> CacheService:
    global _singleton
    if _singleton is None:
        _singleton = CacheService()
    return _singleton


def reset_cache_client() -> None:
    """Test helper: drop singleton so the next ``get_cache()`` reconnects."""
    global _singleton
    _singleton = None
