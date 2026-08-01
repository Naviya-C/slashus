"""Lightweight language detection for routing to the right vector DB.

Script-based and cheap (no model, no LLM). Sinhala is unambiguous by its
Unicode block; extend the mapping as new languages/scripts are added.
"""

from __future__ import annotations

import re

_SINHALA = re.compile(r"[\u0D80-\u0DFF]")
_TAMIL = re.compile(r"[\u0B80-\u0BFF]")
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def detect_language(text: str) -> str:
    """Return an ISO-ish language code. Defaults to 'en' for Latin script."""
    if _SINHALA.search(text):
        return "si"
    if _TAMIL.search(text):
        return "ta"
    if _DEVANAGARI.search(text):
        return "hi"
    return "en"
