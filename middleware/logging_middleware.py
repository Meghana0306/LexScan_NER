"""
HTTP request logging and high-level latency metrics.

Respects ENABLE_REQUEST_LOGGING and ENABLE_METRICS independently.
Skips noisy paths under /static by default.
"""

from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        skip_detail = path.startswith("/static") or path in ("/favicon.ico",)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = getattr(response, "status_code", 200)
            return response
        finally:
            duration = time.perf_counter() - start
            try:
                from config.settings import get_settings

                s = get_settings()
            except Exception:
                return

            if s.enable_metrics and not skip_detail:
                try:
                    from services.metrics import record_http_request

                    record_http_request(request.method, path, status_code, duration)
                except Exception:
                    pass

            if s.enable_request_logging and not skip_detail:
                try:
                    from utils.logger import get_logger

                    if s.enable_logging:
                        get_logger("http").info(
                            "request",
                            extra={
                                "extra": {
                                    "method": request.method,
                                    "path": path,
                                    "status": status_code,
                                    "duration_ms": round(duration * 1000, 2),
                                }
                            },
                        )
                        return
                except Exception:
                    pass
                # Fallback: stdlib
                import logging

                logging.getLogger("lexscan.http").info(
                    "%s %s -> %s in %.2fms",
                    request.method,
                    path,
                    status_code,
                    duration * 1000,
                )
