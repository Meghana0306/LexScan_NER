"""
In-memory request rate limiting for FastAPI middleware.

Disabled unless ENABLE_RATE_LIMIT=true.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}
        self._lock = threading.RLock()

    def is_enabled(self) -> bool:
        try:
            from config.settings import get_settings

            return bool(get_settings().enable_rate_limit)
        except Exception:
            return False

    def check(self, key: str) -> tuple[bool, int, int]:
        try:
            from config.settings import get_settings

            s = get_settings()
        except Exception:
            return True, 0, 0

        limit = max(int(s.rate_limit_requests_per_minute), 1)
        burst = max(int(s.rate_limit_burst), 0)
        max_allowed = limit + burst
        now = time.time()
        window_start = now - 60.0
        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            remaining = max(max_allowed - len(bucket), 0)
            if len(bucket) >= max_allowed:
                return False, remaining, max_allowed
            bucket.append(now)
            remaining = max(max_allowed - len(bucket), 0)
            return True, remaining, max_allowed

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = RateLimiter()

