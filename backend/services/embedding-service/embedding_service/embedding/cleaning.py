"""
embedding/cleaning.py
=====================

Quality filters applied before embedding.

Untitled chunks are usually layout artifacts (cover pages, headers, footers,
printer marks, etc.). For digital documents they are skipped before embedding.

For fully scanned documents, the embedding pipeline passes
require_title=False so these chunks are retained.
"""

from __future__ import annotations

import logging

from contracts import Chunk

log = logging.getLogger(__name__)


def has_title(chunk: Chunk) -> bool:
    """
    True if the chunk is anchored under a heading.
    """
    return (
        bool(chunk.section_path)
        and bool(str(chunk.section_path[0]).strip())
    )


def should_embed(
    chunk: Chunk,
    *,
    require_title: bool,
) -> bool:
    """
    Returns True if the chunk should be embedded.
    """

    if not require_title:
        return True

    if has_title(chunk):
        return True

    log.info(
        "skipping untitled chunk %s (%s)",
        chunk.extra["chunk_id"],
        chunk.type.value,
    )

    return False