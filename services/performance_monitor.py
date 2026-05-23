"""
Optional performance / degradation hints (ENABLE_PERFORMANCE_MONITOR).

Read-only: logs warnings only; does not change model outputs.
"""

from __future__ import annotations

import statistics
import time
from collections import deque
from typing import Any

_MAX_SAMPLES = 500
_recent_durations: dict[str, deque[float]] = {}
_recent_confidences: dict[str, deque[float]] = {}
_last_slow_log: dict[str, float] = {}


def _enabled() -> bool:
    try:
        from config.settings import get_settings

        return bool(get_settings().enable_performance_monitor)
    except Exception:
        return False


def _mean_confidence(entities: list[Any] | None) -> float | None:
    if not entities:
        return None
    scores: list[float] = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        raw = ent.get("score")
        if raw is None:
            raw = ent.get("confidence")
        if raw is None:
            continue
        try:
            scores.append(float(raw))
        except (TypeError, ValueError):
            continue
    if not scores:
        return None
    return float(sum(scores) / len(scores))


def record_analysis(
    route: str,
    duration_wall_seconds: float,
    result: dict[str, Any] | None,
    exc: BaseException | None,
) -> None:
    if not _enabled():
        return
    try:
        from config.settings import get_settings
        from utils.logger import get_logger

        s = get_settings()
        log = get_logger("performance")
    except Exception:
        return

    if exc is not None:
        log.warning("analysis_error", extra={"extra": {"route": route, "error": repr(exc)}})
        return

    if duration_wall_seconds >= s.perf_slow_request_seconds:
        now = time.monotonic()
        if now - _last_slow_log.get(route, 0) > 60:
            _last_slow_log[route] = now
            log.warning(
                "slow_request",
                extra={
                    "extra": {
                        "route": route,
                        "duration_seconds": round(duration_wall_seconds, 3),
                        "threshold": s.perf_slow_request_seconds,
                    }
                },
            )

    dq = _recent_durations.setdefault(route, deque(maxlen=_MAX_SAMPLES))
    dq.append(duration_wall_seconds)

    mc = None
    if result:
        mc = _mean_confidence(result.get("entities"))
        if mc is not None:
            cq = _recent_confidences.setdefault(route, deque(maxlen=_MAX_SAMPLES))
            cq.append(mc)

    if mc is not None and mc < s.perf_min_mean_confidence:
        now = time.monotonic()
        key = f"{route}:low_conf"
        if now - _last_slow_log.get(key, 0) > 300:
            _last_slow_log[key] = now
            log.warning(
                "low_mean_confidence",
                extra={
                    "extra": {
                        "route": route,
                        "mean_confidence": round(mc, 4),
                        "threshold": s.perf_min_mean_confidence,
                    }
                },
            )

    if len(dq) >= 50:
        med = statistics.median(dq)
        if med >= s.perf_slow_request_seconds * 0.85:
            now = time.monotonic()
            key = f"{route}:median_slow"
            if now - _last_slow_log.get(key, 0) > 600:
                _last_slow_log[key] = now
                log.warning(
                    "elevated_median_duration",
                    extra={"extra": {"route": route, "median_duration_s": round(med, 3), "samples": len(dq)}},
                )


def reset_monitor_state() -> None:
    """Test helper."""
    _recent_durations.clear()
    _recent_confidences.clear()
    _last_slow_log.clear()
