"""
Quality filter applied before embedding.

Short chunks are layout debris -- page numbers, running headers, printer marks,
orphaned footnote fragments. Each costs a forward pass, a Qdrant point and an
index slot, and they actively hurt retrieval. Therefore do cleaning.
"""

from __future__ import annotations

import logging
import os

from contracts import Chunk, ChunkType

log = logging.getLogger(__name__)

MIN_WORDS = int(os.getenv("MIN_CHUNK_WORDS", "8"))
_LENGTH_EXEMPT = frozenset({ChunkType.TABLE, ChunkType.IMAGE})


def word_count(text: str) -> int:
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


def should_embed(chunk: Chunk) -> bool:
    text = chunk.embed_text or ""

    if not text.strip():
        log.info("skipping empty chunk %s", chunk.extra.get("chunk_id"))
        return False

    if chunk.type in _LENGTH_EXEMPT:
        return True

    n = word_count(text)
    if n < MIN_WORDS:
        log.info(
            "skipping short chunk %s: %d words < %d",
            chunk.extra.get("chunk_id"),
            n,
            MIN_WORDS,
        )
        return False

    return True