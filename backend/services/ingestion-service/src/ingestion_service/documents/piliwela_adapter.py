from __future__ import annotations

from typing import Any


class PiliwelaConverter:
    """Thin adapter around the published PyPI package; no local Rust build."""

    def __init__(self) -> None:
        import piliwela

        self._package = piliwela

    def convert(self, text: str, font_name: str) -> str:
        if not text.strip():
            return text
        result: Any = self._package.convert_auto_with_metadata(text, font_name)
        if isinstance(result, str):
            return result
        if isinstance(result, tuple) and result and isinstance(result[0], str):
            return result[0]
        for attribute in ("text", "converted_text", "output"):
            value = getattr(result, attribute, None)
            if isinstance(value, str):
                return value
        raise TypeError("unsupported piliwela conversion result")


class IdentityConverter:
    def convert(self, text: str, font_name: str) -> str:
        return text

