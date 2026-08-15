"""Transport-agnostic shapes shared across layers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=False)

    chunk_id: str
    score: float
    content: str
    title: str = ""
    page: int = 0
    doc_id: str = ""
    source: str = ""
    dense_rank: int = 0
    sparse_rank: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)


class SearchOutcome(BaseModel):
    hits: list[SearchHit] = Field(default_factory=list)
    language_used: str = "si"
    collection_used: str = ""
    user_has_no_documents: bool = False
    total_user_chunks: int = 0
    filters_applied: list[str] = Field(default_factory=list)
    degraded: bool = False
    failed: bool = False
    error: str = ""


class TitleInfo(BaseModel):
    title: str
    chunk_count: int = 0


class TitleListing(BaseModel):
    titles: list[TitleInfo] = Field(default_factory=list)
    total_chunks: int = 0
    truncated: bool = False
    failed: bool = False
