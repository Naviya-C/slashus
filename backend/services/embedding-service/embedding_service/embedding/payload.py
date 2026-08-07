"""
PURPOSE
-------
Chunk -> Qdrant payload. This is the contract the agent service reads. Any key
here is a public interface; --- renaming one breaks retrieval silently ---.
"""

from __future__ import annotations

import re
import uuid

from contracts import Chunk

_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
_LESSON_RE = re.compile(r"^\s*(\d+)\s+(.*)$")
_CARRY = ("table_id", "n_rows", "n_cols", "image_id", "storage_key", "storage_url", "width", "height")


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, chunk_id))


def to_payload(c: Chunk) -> dict:
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
