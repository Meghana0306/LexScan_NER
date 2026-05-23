"""Unit tests for ``utils.exceptions``."""

from utils.exceptions import (
    DocumentProcessingError,
    ErrorResponse,
    ExtractionError,
    LexScanError,
    ValidationError,
    format_error_response,
)


def test_lexscan_error_attributes():
    err = LexScanError("oops", code="custom", detail={"x": 1})
    assert err.message == "oops"
    assert err.code == "custom"
    assert err.detail == {"x": 1}


def test_subclass_codes():
    assert DocumentProcessingError("a").code == "document_processing_error"
    assert ExtractionError("a").code == "extraction_error"
    assert ValidationError("a").code == "validation_error"


def test_error_response_from_lexscan_exception():
    er = ErrorResponse.from_exception(ValidationError("bad", detail="x"))
    d = er.as_dict()
    assert d["error"] == "bad"
    assert d["code"] == "validation_error"
    assert d["detail"] == "x"


def test_error_response_from_generic_exception():
    er = ErrorResponse.from_exception(ValueError("nope"))
    d = er.as_dict()
    assert d["error"] == "nope"
    assert d["code"] == "internal_error"


def test_format_error_response():
    body = format_error_response("msg", "code_x", detail=123, extra={"hint": "retry"})
    assert body["error"] == "msg"
    assert body["code"] == "code_x"
    assert body["detail"] == 123
    assert body["hint"] == "retry"
