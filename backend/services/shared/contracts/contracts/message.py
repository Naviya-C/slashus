"""
message.py
==========

One Kafka message represents ONE chunk.

This keeps Kafka messages small, allows parallel embedding,
and enables retries per chunk.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.contracts.contracts.chunk import Chunk, SCHEMA_VERSION


@dataclass(slots=True)
class ChunkCreatedEvent:
    doc_id: str
    user_id: str
    source_name: str
    collection: str
    require_title: bool
    chunk: Chunk

    schema_version: int = field(default=SCHEMA_VERSION)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "doc_id": self.doc_id,
            "user_id": self.user_id,
            "source_name": self.source_name,
            "collection": self.collection,
            "require_title": self.require_title,
            "chunk": self.chunk.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChunkEvent":
        return cls(
            doc_id=d["doc_id"],
            user_id=d["user_id"],
            source_name=d["source_name"],
            collection=d["collection"],
            require_title=d.get("require_title", True),
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            chunk=Chunk.from_dict(d["chunk"]),
        )