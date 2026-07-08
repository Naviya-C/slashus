"""
chunking/fallback_splitter.py
=============================

PURPOSE
-------
Split ONE oversized block into pieces that each fit the token budget. Used only
when a single block exceeds the budget -- the block chunker calls this as a
fallback, not as the main path.

It is token-aware (uses the same tokenizer as the budget) and recursive in
granularity: sentence -> word -> character, stopping as soon as pieces fit.
Sentence splitting understands both Latin '.?!' and the Sinhala danda '.'.
"""

from __future__ import annotations

import re

# split on sentence enders (Latin + Sinhala danda U+0964) or newlines
_SENTENCE_RE = re.compile(r"(?<=[.!?\u0964])\s+|\n+")


def _pack(units: list[str], count, max_tokens: int, joiner: str) -> list[str]:
    """Greedily pack units up to the budget. An oversized single unit is emitted
    alone (the caller recurses to a finer granularity for it)."""
    out: list[str] = []
    cur: list[str] = []
    for u in units:
        if not u:
            continue
        candidate = joiner.join(cur + [u]) if cur else u
        if cur and count(candidate) > max_tokens:
            out.append(joiner.join(cur))
            cur = [u]
        else:
            cur.append(u)
    if cur:
        out.append(joiner.join(cur))
    return out


def _char_split(text: str, max_tokens: int) -> list[str]:
    """Last resort for a delimiter-less giant string: slice by a char estimate."""
    approx = max(1, max_tokens * 4)
    return [text[i:i + approx] for i in range(0, len(text), approx)]


def recursive_split(text: str, count, max_tokens: int) -> list[str]:
    """Split `text` into pieces each within `max_tokens`, finest granularity last."""
    if count(text) <= max_tokens:
        return [text]

    # 1. pack by sentences
    sentences = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
    pieces = _pack(sentences, count, max_tokens, joiner=" ")

    # 2. any still too big -> pack by words
    step2: list[str] = []
    for p in pieces:
        step2.extend([p] if count(p) <= max_tokens else _pack(p.split(), count, max_tokens, " "))

    # 3. any STILL too big (no spaces) -> char split
    out: list[str] = []
    for p in step2:
        out.extend([p] if count(p) <= max_tokens else _char_split(p, max_tokens))
    return out