"""
embedding/cleaning.py
=====================

PURPOSE
-------
Final quality gate between chunking and Qdrant. A chunk with NO title
(empty section_path -> lesson_title=None in the payload) is usually junk the
layout stage couldn't anchor to any heading: cover pages, printer marks,
publisher notes, stray page furniture. Storing them pollutes retrieval, so
they are dropped here — before embedding, which also saves embedding calls.

INTERPLAY WITH OCR
------------------
OCR chunks inherit the heading breadcrumb carried over from the last digital
page. If an ENTIRE document is scanned, no headings exist and every chunk is
untitled — dropping them would store nothing. That's why `require_title` is a
parameter on embed_and_store(): flip it off for fully-scanned documents.
"""

from __future__ import annotations

import logging
from collections import Counter

from src.ingestion.models.chunk import Chunk

log = logging.getLogger(__name__)


def has_title(c: Chunk) -> bool:
    """True when the chunk is anchored under a real heading."""
    return bool(c.section_path) and bool(str(c.section_path[0]).strip())


def drop_untitled(chunks: list[Chunk]) -> list[Chunk]:
    """Remove chunks with no title. Logs what was dropped, per chunk type."""
    kept = [c for c in chunks if has_title(c)]

    dropped = len(chunks) - len(kept)
    if dropped:
        by_type = Counter(c.type.value for c in chunks if not has_title(c))
        log.info(
            "cleaning: dropped %d untitled chunk(s) before store: %s",
            dropped,
            dict(by_type),
        )
    return kept
