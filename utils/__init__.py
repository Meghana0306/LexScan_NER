"""Shared utilities for production enhancements (opt-in)."""

from utils.exceptions import (
    DocumentProcessingError,
    ErrorResponse,
    ExtractionError,
    LexScanError,
    ValidationError,
)
from utils.logger import JsonFormatter, configure_logging, get_logger

__all__ = [
    "LexScanError",
    "DocumentProcessingError",
    "ExtractionError",
    "ValidationError",
    "ErrorResponse",
    "JsonFormatter",
    "configure_logging",
    "get_logger",
]
