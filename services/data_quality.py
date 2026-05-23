"""
Data quality assessments: warnings only, never blocks processing.

Enable with ENABLE_DATA_QUALITY=true (logs via structured logger when
ENABLE_LOGGING is also true; otherwise uses stdlib logging WARNING).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from config.settings import get_settings
from utils.validators import sniff_language_hint, validate_document_text


@dataclass
class DataQualityReport:
    warnings: list[str] = field(default_factory=list)
    hints: dict[str, str] = field(default_factory=dict)


def assess_text(text: str | None) -> DataQualityReport:
    """Return non-blocking quality hints for arbitrary document text."""
    report = DataQualityReport()
    if text is None:
        report.warnings.append("text is None")
        return report
    if not isinstance(text, str):
        report.warnings.append("text is not a string")
        return report

    v = validate_document_text(text, check_pii=True)
    report.warnings.extend(v.warnings)
    if not v.valid:
        report.warnings.extend(v.errors)

    n = len(text)
    if n > 500_000:
        report.warnings.append(f"Very long document ({n} chars); processing may be slow")
    elif n < 20:
        report.hints["length"] = "short_text"

    lang = sniff_language_hint(text)
    if lang:
        report.hints["script_hint"] = lang

    if "\x00" in text:
        report.warnings.append("Null bytes present; possible binary corruption")

    return report


def log_data_quality_warnings(text: str | None, *, context: str) -> None:
    if not get_settings().enable_data_quality:
        return
    try:
        report = assess_text(text)
        if not report.warnings and not report.hints:
            return
        payload = {"context": context, "warnings": report.warnings, "hints": report.hints}
        try:
            from utils.logger import get_logger

            if get_settings().enable_logging:
                get_logger("data_quality").warning("data_quality_report", extra={"extra": payload})
                return
        except Exception:
            pass
        logging.getLogger("lexscan.data_quality").warning("%s", payload)
    except Exception:
        pass
