"""
chunk.py
==================

The wire schema shared by the ingestion and embedding services. This used to be
src/ingestion/models/chunk.py; it now lives in ONE place so the producer and the
consumer can never drift apart.

Rule: any change here is a change to the message format both services speak.
Bump SCHEMA_VERSION when you add/rename/remove a field, and let the consumer
decide what to do with an older/newer version.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum

SCHEMA_VERSION = 1


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

    # --- serialization: use THESE on both sides, never hand-roll json ---

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value         
        d["bbox"] = list(self.bbox) if self.bbox is not None else None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        bbox = d.get("bbox")
        return cls(
            text=d["text"],
            embed_text=d["embed_text"],
            type=ChunkType(d["type"]),
            section_path=list(d.get("section_path") or []),
            page=d.get("page"),
            bbox=tuple(bbox) if bbox is not None else None,   # list -> tuple back
            chunk_index=d["chunk_index"],
            token_count=d["token_count"],
            extra=dict(d.get("extra") or {}),
        )