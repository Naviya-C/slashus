"""
adapters/null_adapters.py
=========================

PURPOSE
-------
No-op stand-ins for every port, so the pipeline runs with NO LLM key, NO cloud,
and NO piliwela build. They let you ingest today and add real services later
without changing any call site.

They rely on the pipeline's existing fallbacks:
    - NullSummarizer/NullCaptioner return "" -> the enrichment stages already
      fall back to a deterministic placeholder ("Table with N rows...", "Image (WxH)...").
    - NullConverter returns text unchanged (fine for English/testing; NOT for real
      legacy Sinhala -- that needs piliwela).
    - NullStorage keeps bytes in memory (nothing written to disk or cloud).
"""

from __future__ import annotations


class NullConverter:
    """No piliwela: return text unchanged. Dev/test only -- legacy Sinhala won't convert."""
    def convert(self, text: str, font: str) -> str:
        return text


class NullSummarizer:
    """No LLM: return blank so summarize_tables uses its deterministic fallback."""
    def summarize(self, markdown: str, context: str = "") -> str:
        return ""


class NullCaptioner:
    """No vision LLM: return blank so caption_images uses its deterministic fallback."""
    def caption(self, image_bytes: bytes, mime_type: str, context: str = "") -> str:
        return ""


class NullStorage:
    """In-memory Storage: nothing hits disk or cloud. Bytes live for the process only."""
    def __init__(self) -> None:
        self._d: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> str:
        self._d[key] = data
        return self.url(key)

    def get(self, key: str) -> bytes:
        return self._d[key]

    def url(self, key: str) -> str:
        return f"mem://{key}"

    def delete_prefix(self, prefix: str) -> int:
        keys = [k for k in self._d if k.startswith(prefix)]
        for k in keys:
            del self._d[k]
        return len(keys)