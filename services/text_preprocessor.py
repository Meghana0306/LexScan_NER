"""
Optional light-weight text normalization before NER (ENABLE_PREPROCESSING).

Conservative: does not remove content, only normalizes whitespace and unicode.
"""

from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"[ \t]+")
_LINE_END_RE = re.compile(r"\r\n|\r")


def preprocess_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    t = unicodedata.normalize("NFC", text)
    t = _LINE_END_RE.sub("\n", t)
    # normalize unicode dashes and quotes to common ASCII forms (optional normalization)
    t = t.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    t = t.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    lines = []
    for line in t.split("\n"):
        lines.append(_WS_RE.sub(" ", line).rstrip())
    t = "\n".join(lines)
    return t.strip()
