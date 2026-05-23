"""
Reusable validation helpers (opt-in).

Nothing here is applied automatically to ``app.py`` / ``ui.py``. Import and
call explicitly when enabling ``ENABLE_VALIDATION`` in your own integration layer.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from config.settings import get_settings

# --- Heuristic PII patterns (warnings only) ---
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _detect_pii_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    if _SSN_RE.search(text):
        warnings.append("Possible US SSN pattern detected")
    if _EMAIL_RE.search(text):
        warnings.append("Email-like pattern detected")
    if _CC_RE.search(text):
        warnings.append("Possible payment-card-like digit sequence detected")
    return warnings


def validate_document_text(
    text: str | None,
    *,
    max_chars: int | None = None,
    check_pii: bool = True,
    check_encoding: bool = True,
) -> ValidationResult:
    """
    Validate raw document text.

    - Empty / non-string ? invalid
    - Length over ``max_chars`` (default from settings) ? invalid
    - Non-Unicode normalization issues ? warnings
    - PII-like patterns ? warnings (do not block)
    """
    settings = get_settings()
    limit = max_chars if max_chars is not None else settings.max_document_chars
    errors: list[str] = []
    warnings: list[str] = []

    if text is None:
        return ValidationResult(valid=False, errors=["Document text is missing"])

    if not isinstance(text, str):
        return ValidationResult(valid=False, errors=["Document text must be a string"])

    if not text.strip():
        return ValidationResult(valid=False, errors=["Document text is empty"])

    if len(text) > limit:
        errors.append(f"Document exceeds maximum length ({len(text)} > {limit})")

    if check_encoding:
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            errors.append("Text contains characters that cannot be encoded as UTF-8")

        # Surrogate pairs would indicate broken decoding
        if any(ord(ch) in range(0xD800, 0xE000) for ch in text):
            warnings.append("Text contains surrogate code points; possible decoding issue")

    if check_pii:
        warnings.extend(_detect_pii_warnings(text))

    normalized = unicodedata.normalize("NFC", text)
    if normalized != text:
        warnings.append("Unicode normalization (NFC) would change the text")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_file_upload(
    *,
    filename: str | None,
    size_bytes: int | None,
    content_type: str | None = None,
    allowed_extensions: frozenset[str] | None = None,
    max_bytes: int | None = None,
) -> ValidationResult:
    """Validate an uploaded file's metadata (not virus scanning)."""
    settings = get_settings()
    max_b = max_bytes if max_bytes is not None else settings.max_upload_bytes
    allowed = allowed_extensions or frozenset({".pdf", ".docx", ".doc", ".txt", ".text"})
    errors: list[str] = []
    warnings: list[str] = []

    if not filename:
        errors.append("Filename is missing")
        return ValidationResult(valid=False, errors=errors)

    suffix = Path(filename).suffix.lower()
    if suffix not in allowed:
        errors.append(f"File extension {suffix or '(none)'} is not allowed")

    if size_bytes is None:
        warnings.append("Upload size unknown; could not verify limits")
    elif size_bytes < 0:
        errors.append("Invalid negative file size")
    elif size_bytes > max_b:
        errors.append(f"File too large ({size_bytes} bytes > {max_b})")

    if content_type:
        ct = content_type.lower()
        if "pdf" not in ct and "word" not in ct and "officedocument" not in ct and "text" not in ct and "octet-stream" not in ct:
            warnings.append(f"Unusual Content-Type for documents: {content_type}")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_entity_data(
    entities: Any,
    *,
    require_score: bool = False,
) -> ValidationResult:
    """
    Validate a list of entity dicts typically produced by NER post-processing.

    Expected shape per item: ``{"text": str, "label": str, ...}``
    """
    errors: list[str] = []
    warnings: list[str] = []

    if entities is None:
        return ValidationResult(valid=False, errors=["entities is None"])

    if not isinstance(entities, list):
        return ValidationResult(valid=False, errors=["entities must be a list"])

    for i, ent in enumerate(entities):
        if not isinstance(ent, dict):
            errors.append(f"Entity at index {i} is not an object")
            continue
        text = ent.get("text") or ent.get("word") or ent.get("entity")
        label = ent.get("label") or ent.get("entity_group")
        if not text or not isinstance(text, str):
            errors.append(f"Entity at index {i} missing string 'text'")
        if not label or not isinstance(label, str):
            errors.append(f"Entity at index {i} missing string 'label'")
        if require_score and "score" not in ent and "confidence" not in ent:
            warnings.append(f"Entity at index {i} has no score/confidence field")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def sniff_language_hint(text: str) -> str | None:
    """
    Extremely lightweight language hint (not a substitute for a real detector).

    Returns ``"mostly_latin"``, ``"cjk"``, ``"arabic"``, or ``None``.
    """
    if not text:
        return None
    sample = text[:2000]
    if re.search(r"[\u0600-\u06FF]", sample):
        return "arabic"
    if re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", sample):
        return "cjk"
    if re.search(r"[A-Za-z]", sample):
        return "mostly_latin"
    return None


def validate_binary_readable(stream: BinaryIO, *, max_read: int = 65536) -> ValidationResult:
    """Read a small prefix to detect obviously corrupted / empty binaries."""
    warnings: list[str] = []
    errors: list[str] = []
    try:
        pos = stream.tell()
    except Exception:
        pos = 0
    try:
        chunk = stream.read(max_read)
    except OSError as e:
        return ValidationResult(valid=False, errors=[f"Could not read upload: {e}"])
    finally:
        try:
            stream.seek(pos)
        except Exception:
            pass

    if not chunk:
        errors.append("File appears empty")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
