"""
In-memory model cache for optional reuse across requests.

This module does not change existing model-loading code on its own.
Callers can opt in with ``ENABLE_MODEL_CACHE=true`` and wrap their
existing loader functions with ``get_or_load``.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CacheEntry:
    value: Any
    loaded_at: float
    expires_at: float | None
    hits: int = 0


class ModelCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    def _enabled(self) -> bool:
        try:
            from config.settings import get_settings

            return bool(get_settings().enable_model_cache)
        except Exception:
            return False

    def _ttl_seconds(self, override: int | None = None) -> int | None:
        if override is not None:
            return max(int(override), 0)
        try:
            from config.settings import get_settings

            return max(int(get_settings().model_cache_ttl_seconds), 0)
        except Exception:
            return 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at is not None and entry.expires_at <= time.time():
                self._entries.pop(key, None)
                return None
            entry.hits += 1
            return entry.value

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> Any:
        ttl = self._ttl_seconds(ttl_seconds)
        if ttl_seconds is not None and ttl is not None and ttl <= 0:
            expires_at = time.time()
        else:
            expires_at = None if ttl is None or ttl <= 0 else time.time() + ttl
        with self._lock:
            self._entries[key] = CacheEntry(value=value, loaded_at=time.time(), expires_at=expires_at)
        return value

    def get_or_load(self, key: str, loader: Callable[[], Any], *, ttl_seconds: int | None = None) -> Any:
        if not self._enabled():
            return loader()
        cached = self.get(key)
        if cached is not None:
            return cached
        with self._lock:
            cached = self.get(key)
            if cached is not None:
                return cached
            value = loader()
            return self.set(key, value, ttl_seconds=ttl_seconds)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def clear_expired(self) -> int:
        removed = 0
        now = time.time()
        with self._lock:
            for key in list(self._entries.keys()):
                entry = self._entries.get(key)
                if entry is not None and entry.expires_at is not None and entry.expires_at <= now:
                    self._entries.pop(key, None)
                    removed += 1
        return removed

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled(),
                "size": len(self._entries),
                "keys": sorted(self._entries.keys()),
                "hits": {key: entry.hits for key, entry in self._entries.items()},
            }


model_cache = ModelCache()
