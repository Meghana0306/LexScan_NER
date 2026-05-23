"""ASGI middleware for LexScan (opt-in)."""

from middleware.logging_middleware import RequestLoggingMiddleware

__all__ = ["RequestLoggingMiddleware"]
