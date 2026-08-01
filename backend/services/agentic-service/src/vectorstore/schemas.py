"""Search request/response shapes.

Deliberately transport-agnostic dataclasses rather than the generated protobuf
messages. The retrieval agent and ranking layer depend on these, so swapping
the transport again later touches one file instead of five.

Language routing moved into embedding-service — it owns the collections, so it
decides which one a language maps to. `language` remains on the request as the
routing key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchRequest:
    query: str
    language: str                       # selects the target database
    limit: int = 10
    filters: dict[str, Any] = field(default_factory=dict)
    mode: str = "hybrid"                # "hybrid" | "dense" | "sparse"


@dataclass(slots=True)
class SearchHit:
    chunk_id: str
    score: float
    content: str
    title: str = ""
    page: int = 0
    source: str = ""                    # "bm25", "semantic", "bm25+semantic"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResponse:
    hits: list[SearchHit]
    language_used: str
    collection_used: str
