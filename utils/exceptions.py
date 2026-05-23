"""
Custom exceptions and a consistent JSON-friendly error envelope.

These are optional; existing FastAPI routes are unchanged unless you
explicitly raise or return these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping


class LexScanError(Exception):
    """Base type for LexScan application errors."""

    code: str = "lexscan_error"

    def __init__(self, message: str, *, code: str | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.detail = detail


class DocumentProcessingError(LexScanError):
    """Raised when a document cannot be processed end-to-end."""

    code = "document_processing_error"


class ExtractionError(DocumentProcessingError):
    """Raised when text extraction from a file fails."""

    code = "extraction_error"


class ValidationError(LexScanError):
    """Raised when user or API input fails validation."""

    code = "validation_error"


@dataclass
class ErrorResponse:
    """Stable error payload for APIs and logging."""

    error: str
    code: str
    detail: Any | None = None
    extra: MutableMapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.error, "code": self.code}
        if self.detail is not None:
            body["detail"] = self.detail
        if self.extra:
            body.update(dict(self.extra))
        return body

    @classmethod
    def from_exception(cls, exc: Exception, *, code: str | None = None) -> ErrorResponse:
        if isinstance(exc, LexScanError):
            return cls(error=exc.message, code=code or exc.code, detail=exc.detail)
        return cls(error=str(exc), code=code or "internal_error", detail=None)


def format_error_response(
    message: str,
    code: str,
    *,
    detail: Any = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Helper for FastAPI ``JSONResponse`` bodies."""
    return ErrorResponse(
        error=message,
        code=code,
        detail=detail,
        extra=dict(extra or {}),
    ).as_dict()
