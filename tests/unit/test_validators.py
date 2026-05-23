"""Unit tests for ``utils.validators``."""

import io

import pytest

from config.settings import clear_settings_cache
from utils.validators import (
    validate_binary_readable,
    validate_document_text,
    validate_entity_data,
    validate_file_upload,
    sniff_language_hint,
)


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_validate_document_text_empty():
    r = validate_document_text("")
    assert not r.valid
    assert r.errors


def test_validate_document_text_too_long(monkeypatch):
    monkeypatch.setenv("MAX_DOCUMENT_CHARS", "10")
    clear_settings_cache()
    r = validate_document_text("x" * 11)
    assert not r.valid
    assert any("exceeds" in e for e in r.errors)


def test_validate_document_text_pii_warning():
    r = validate_document_text("Contact: user@example.com about the case.", check_pii=True)
    assert r.valid
    assert any("Email" in w for w in r.warnings)


def test_validate_file_upload_bad_ext():
    r = validate_file_upload(filename="x.exe", size_bytes=100)
    assert not r.valid


def test_validate_file_upload_ok():
    r = validate_file_upload(filename="doc.pdf", size_bytes=1024)
    assert r.valid


def test_validate_entity_data_ok():
    r = validate_entity_data([{"text": "John", "label": "PER", "score": 0.9}])
    assert r.valid


def test_validate_entity_data_bad_shape():
    r = validate_entity_data([{"text": "John"}])
    assert not r.valid


def test_sniff_language_hint():
    assert sniff_language_hint("Hello world") == "mostly_latin"
    assert sniff_language_hint("\u4f60\u597d") == "cjk"


def test_validate_binary_readable_empty():
    stream = io.BytesIO(b"")
    r = validate_binary_readable(stream)
    assert not r.valid
