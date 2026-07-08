"""
chunking/token_estimate.py
==========================

PURPOSE
-------
A local, model-free token estimate for the chunk budget. Since Gemini does the
embeddings (large token limit ~2048), we do NOT load a HuggingFace tokenizer just
to size chunks -- that dependency and its model download are gone.

This is an APPROXIMATE word-based proxy: fast, offline, good enough for keeping
chunks within a safe budget. It is deliberately rough.

CAVEAT
------
Subword tokenizers split words into more tokens than this counts, and Sinhala
expands more than English. So keep max_tokens comfortably below Gemini's real
limit. If you ever need exactness, inject a precise counter into
chunk_blocks(count=...) -- e.g. Gemini's count_tokens, run offline/batched, never
on the hot path.
"""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough token count for budgeting (word-based, no model)."""
    return len(text.split())