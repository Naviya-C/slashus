"""
embedding/payload.py
====================

PURPOSE
-------
Chunk -> Qdrant payload. This IS the contract the agent service reads. Any key
here is a public interface; renaming one breaks retrieval silently.

NOTES
-----
- Doc-level fields (chunk_id, doc_id, user_id, source_name) are stamped by
  ingest._stamp(), so they are always present -- indexed access is deliberate.
- Type-specific fields (storage_key for images, table_id for tables) are carried
  through, or the agent retrieves an image caption with no way to show the image.
- content_type is a placeholder until sections.py keeps level-2 headings; the
  exercise marker (ලිඛිත අභ්‍යාස) is not currently captured.
"""

from __future__ import annotations

import re
import uuid

from contracts import Chunk

_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
_LESSON_RE = re.compile(r"^\s*(\d+)\s+(.*)$")

# type-specific extras written by side_chunks.table_to_chunk / image_to_chunk
_CARRY = ("table_id", "n_rows", "n_cols", "image_id", "storage_key", "storage_url", "width", "height")


def point_id(chunk_id: str) -> str:
    """Qdrant takes uint or UUID only -- 'doc:12' is neither. Deterministic, so a
    re-ingest overwrites the same points instead of duplicating them."""
    return str(uuid.uuid5(_NAMESPACE, chunk_id))


def to_payload(c: Chunk) -> dict:
    """Chunk -> payload dict. Embedding uses c.embed_text; this stores c.text."""
    title = c.section_path[0] if c.section_path else None
    lesson_no, lesson_title = None, title
    if title:
        m = _LESSON_RE.match(title)
        if m:
            lesson_no, lesson_title = int(m.group(1)), m.group(2).strip()

    payload = {
        "text": c.text,
        "lesson_title": lesson_title,
        "page_number": c.page,
        "block_type": c.type.value,
        "chunk_index": c.chunk_index,
        "token_count": c.token_count,
        "chunk_id": c.extra["chunk_id"],
        "doc_id": c.extra["doc_id"],
        "user_id": c.extra["user_id"],
        "source_file": c.extra["source_name"],
    }
    payload.update({k: c.extra[k] for k in _CARRY if k in c.extra})
    return payload
