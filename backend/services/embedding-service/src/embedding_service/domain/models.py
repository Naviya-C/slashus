"""Domain model. The Qdrant payload is a cross-service contract."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

POINT_ID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class BlockType(StrEnum):
    TEXT = "text"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    IMAGE = "image"
    LIST = "list"
    CAPTION = "caption"


class SearchMode(StrEnum):
    HYBRID = "hybrid"
    DENSE = "dense"
    SPARSE = "sparse"


NonEmptyStr = Annotated[str, Field(min_length=1)]


class SparseVector(BaseModel):
    model_config = ConfigDict(frozen=True)

    indices: list[int] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)

    @model_validator(mode="after")
    def _same_length(self) -> Self:
        if len(self.indices) != len(self.values):
            raise ValueError("sparse indices and values must be the same length")
        return self

    def is_empty(self) -> bool:
        return not self.indices


class IngestChunk(BaseModel):
    """Validated at the Kafka boundary so a malformed event fails one message
    rather than the whole batch."""

    model_config = ConfigDict(extra="allow")

    chunk_id: NonEmptyStr
    doc_id: NonEmptyStr
    user_id: NonEmptyStr
    text: str = ""
    embed_text: str = ""
    source_name: str = ""
    page: int | None = None
    chunk_index: int = 0
    token_count: int = 0
    block_type: BlockType = BlockType.TEXT
    section_path: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _embed_text_defaults(self) -> Self:
        if not self.embed_text:
            object.__setattr__(self, "embed_text", self.text)
        return self

    @property
    def point_id(self) -> str:
        # Deterministic: a Kafka replay overwrites its own point instead of
        # creating a duplicate. This is what makes at-least-once safe.
        return str(uuid.uuid5(POINT_ID_NAMESPACE, self.chunk_id))


class ChunkPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str
    chunk_id: str
    doc_id: str
    user_id: str
    lesson_title: str | None = None
    lesson_number: int | None = None
    page_number: int | None = None
    block_type: str = BlockType.TEXT.value
    chunk_index: int = 0
    token_count: int = 0
    source_file: str = ""

    def to_qdrant(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=False)


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    score: float
    content: str
    title: str = ""
    page: int = 0
    doc_id: str = ""
    source: str = ""
    extra: dict[str, str] = Field(default_factory=dict)
    dense_rank: int = 0
    sparse_rank: int = 0


class SearchResult(BaseModel):
    hits: list[SearchHit] = Field(default_factory=list)
    collection_used: str = ""
    language_used: str = "si"
    user_has_no_documents: bool = False
    total_user_chunks: int = 0
    filters_applied: list[str] = Field(default_factory=list)
    degraded: bool = False


class TitleInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    title: str
    chunk_count: int = 0


class TitleListing(BaseModel):
    titles: list[TitleInfo] = Field(default_factory=list)
    total_chunks: int = 0
    truncated: bool = False
