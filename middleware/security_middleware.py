"""
Optional API-key auth and rate limiting.

Designed to protect API endpoints without affecting the default local UI
experience unless flags are explicitly enabled.
"""

from __future__ import annotations

from typing import Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            from config.settings import get_settings

            settings = get_settings()
        except Exception:
            return await call_next(request)

        path = request.url.path
        if self._is_exempt(path, settings.auth_exempt_paths):
            return await call_next(request)

        if settings.enable_api_key_auth and path.startswith("/api"):
            provided = request.headers.get("x-api-key") or request.query_params.get("api_key")
            if not provided or provided not in settings.api_keys:
                return JSONResponse({"error": "unauthorized"}, status_code=401)

        if settings.enable_rate_limit and path.startswith("/api"):
            try:
                from services.rate_limiter import rate_limiter

                client_host = request.client.host if request.client else "unknown"
                allowed, remaining, limit = rate_limiter.check(client_host)
                if not allowed:
                    return JSONResponse(
                        {"error": "rate limit exceeded", "remaining": remaining, "limit": limit},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )
            except Exception:
                pass

        return await call_next(request)

    def _is_exempt(self, path: str, exempt_paths: tuple[str, ...]) -> bool:
        for prefix in exempt_paths:
            if prefix == path:
                return True
            if prefix.endswith("*") and path.startswith(prefix[:-1]):
                return True
            if prefix and path.startswith(prefix.rstrip("/")) and prefix in ("/static", "/static/*"):
                return True
        return False
