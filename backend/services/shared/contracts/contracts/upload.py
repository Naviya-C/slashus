"""
contracts/uploaded.py
=====================

The message the UPLOAD service emits and the INGESTION service consumes. It does
NOT carry the PDF bytes — those go to object storage; this just points at them.
Ingestion reads storage_key to fetch the file, and doc_id/user_id flow all the
way through to the Qdrant payload for tenant filtering.

Both ids are UUID strings (the upload service generates doc_id; user_id comes
from the authenticated caller).
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1


@dataclass
class DocUploaded:
    doc_id: str            # uuid4, minted by the upload service
    user_id: str           # uuid of the uploading user (tenant scope)
    source_name: str       # original filename, e.g. "grade10-science.pdf"
    storage_key: str       # where the PDF lives, e.g. "{user_id}/{doc_id}/source.pdf"
    content_type: str = "application/pdf"
    schema_version: int = field(default=SCHEMA_VERSION)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "doc_id": self.doc_id,
            "user_id": self.user_id,
            "source_name": self.source_name,
            "storage_key": self.storage_key,
            "content_type": self.content_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DocUploaded":
        return cls(
            doc_id=d["doc_id"],
            user_id=d["user_id"],
            source_name=d["source_name"],
            storage_key=d["storage_key"],
            content_type=d.get("content_type", "application/pdf"),
            schema_version=d.get("schema_version", 1),
        )