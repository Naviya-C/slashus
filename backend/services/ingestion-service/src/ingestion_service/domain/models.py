from __future__ import annotations

import hashlib
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = 2
POINT_ID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class BlockType(StrEnum):
    TEXT = "text"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"


class JobStatus(StrEnum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    PARTIALLY_SEARCHABLE = "partially_searchable"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUploadedEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    doc_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    storage_key: str = Field(min_length=1)
    content_type: str = "application/octet-stream"
    job_id: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)

    @field_validator("storage_key")
    @classmethod
    def safe_storage_key(cls, value: str) -> str:
        if value.startswith("/") or ".." in value.split("/"):
            raise ValueError("unsafe storage key")
        return value

    @property
    def effective_job_id(self) -> str:
        return self.job_id or self.doc_id


class ExtractedBlock(BaseModel):
    block_type: BlockType
    text: str = ""
    section_path: list[str] = Field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Asset(BaseModel):
    data: bytes = Field(exclude=True)
    extension: str
    content_type: str
    width: int
    height: int
    bbox: tuple[float, float, float, float] | None = None
    ocr_text: str = ""
    digest: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.digest:
            object.__setattr__(self, "digest", hashlib.sha256(self.data).hexdigest())


class DocumentUnit(BaseModel):
    number: int = Field(ge=1)
    label: str
    blocks: list[ExtractedBlock] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    text: str
    embed_text: str
    type: BlockType
    lesson_title: str | None = None
    section_path: list[str] = Field(default_factory=list)
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    chunk_index: int
    token_count: int
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def derive_lesson_title(self) -> "Chunk":
        if self.lesson_title is None and self.section_path:
            self.lesson_title = self.section_path[0]
        return self

    def wire_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["block_type"] = self.type.value
        return data


class ChunkCreatedEvent(BaseModel):
    schema_version: int = SCHEMA_VERSION
    doc_id: str
    user_id: str
    source_name: str
    require_title: bool = False
    chunk: Chunk

    def wire_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["chunk"] = self.chunk.wire_dict()
        return data


class ImageEnrichmentRequested(BaseModel):
    schema_version: int = SCHEMA_VERSION
    doc_id: str
    user_id: str
    source_name: str
    chunk_id: str
    chunk_index: int
    page: int | None
    section_path: list[str] = Field(default_factory=list)
    storage_key: str
    content_type: str
    image_sha256: str
    fallback_text: str


class DocumentIngestedEvent(BaseModel):
    schema_version: int = SCHEMA_VERSION
    doc_id: str
    user_id: str
    job_id: str
    source_name: str
    units_processed: int
    chunks_published: int
    images_queued: int


class JobState(BaseModel):
    job_id: str
    doc_id: str
    user_id: str
    source_name: str
    status: JobStatus
    units_processed: int = 0
    units_total: int | None = None
    chunks_published: int = 0
    images_queued: int = 0
    attempts: int = 0
    error: str | None = None
    started_at: str | None = None
    updated_at: str
    completed_at: str | None = None


def stable_chunk_id(doc_id: str, unit: int, block_type: BlockType, ordinal: int) -> str:
    logical = f"{doc_id}:{unit}:{block_type.value}:{ordinal}"
    return str(uuid.uuid5(POINT_ID_NAMESPACE, logical))
