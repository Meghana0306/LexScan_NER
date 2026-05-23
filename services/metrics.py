"""
Prometheus-compatible metrics (opt-in via ENABLE_METRICS).

Safe to import when ``prometheus_client`` is missing: recording becomes a no-op.
"""

from __future__ import annotations

_HAVE = False
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    _HAVE = True
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain"
    Counter = Histogram = None  # type: ignore

_DOCS = None
_ERRORS = None
_ROUTE_DURATION = None
_HTTP_DURATION = None
_ENTITY_COUNT = None


def _ensure_metrics() -> bool:
    global _DOCS, _ERRORS, _ROUTE_DURATION, _HTTP_DURATION, _ENTITY_COUNT
    if not _HAVE:
        return False
    if _DOCS is None:
        _DOCS = Counter(
            "lexscan_documents_processed_total",
            "Document analyses completed",
            labelnames=("endpoint",),
        )
        _ERRORS = Counter(
            "lexscan_handler_errors_total",
            "Unhandled errors in LexScan handlers",
            labelnames=("endpoint",),
        )
        _ROUTE_DURATION = Histogram(
            "lexscan_route_duration_seconds",
            "Wall time for LexScan document routes",
            labelnames=("endpoint",),
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, float("inf")),
        )
        _HTTP_DURATION = Histogram(
            "lexscan_http_request_duration_seconds",
            "HTTP request duration",
            labelnames=("method", "path_group", "status"),
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, float("inf")),
        )
        _ENTITY_COUNT = Histogram(
            "lexscan_entity_count",
            "Entities extracted per analysis",
            buckets=(0, 1, 2, 5, 10, 20, 50, 100, 200, 500, float("inf")),
        )
    return True


def _metrics_enabled() -> bool:
    try:
        from config.settings import get_settings

        return bool(get_settings().enable_metrics)
    except Exception:
        return False


def record_route_finished(
    endpoint: str,
    duration_seconds: float,
    result: dict | None,
    exc: BaseException | None,
) -> None:
    if not _metrics_enabled() or not _ensure_metrics():
        return
    assert _DOCS is not None and _ERRORS is not None and _ROUTE_DURATION is not None and _ENTITY_COUNT is not None
    if exc is not None:
        _ERRORS.labels(endpoint=endpoint).inc()
        return
    _DOCS.labels(endpoint=endpoint).inc()
    _ROUTE_DURATION.labels(endpoint=endpoint).observe(max(duration_seconds, 0.0))
    if result and isinstance(result.get("entity_count"), (int, float)):
        _ENTITY_COUNT.observe(float(result["entity_count"]))


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    if not _metrics_enabled() or not _ensure_metrics():
        return
    assert _HTTP_DURATION is not None
    group = _path_group(path)
    _HTTP_DURATION.labels(method=method, path_group=group, status=str(status_code)).observe(max(duration_seconds, 0.0))


def _path_group(path: str) -> str:
    if path.startswith("/static"):
        return "/static/*"
    if path == "/":
        return "/"
    return path


def render_metrics_payload() -> tuple[bytes, str] | None:
    """Return (body, content_type) or None if unavailable."""
    if not _metrics_enabled() or not _HAVE:
        return None
    _ensure_metrics()
    return generate_latest(), CONTENT_TYPE_LATEST
