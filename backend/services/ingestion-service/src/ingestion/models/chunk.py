"""
models/chunk.py
===============

PURPOSE
-------
The OUTPUT contract of the whole pipeline. Every stage -- text, tables, images --
funnels into a Chunk, so downstream (embed, Qdrant, Postgres) sees ONE shape.

    text          the content (what you return / feed the LLM)
    embed_text    what you actually embed (for text = content, optionally with a
                  section breadcrumb; for tables = the summary; for images = caption)
    type          text | table | image
    section_path  heading breadcrumb, e.g. ["Chapter 3", "Photosynthesis"]
    page          page number (clean, because chunking is per page)
    bbox          position on the page
    chunk_index   order within the document
    token_count   size of `text` in the embedding model's tokens

Doc-level fields (chunk_id, doc_id, user_id, source_name) are added by the
orchestrator at assembly time -- the chunker doesn't know them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


@dataclass
class Chunk:
    text: str
    embed_text: str
    type: ChunkType
    section_path: list[str]
    page: int | None
    bbox: tuple | None
    chunk_index: int
    token_count: int
    extra: dict = field(default_factory=dict)