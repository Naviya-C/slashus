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
    # Two kinds of key live in here, and they are treated very differently
    # downstream:
    #
    #   OWNERSHIP  user_id, doc_id   — never dropped, promoted to typed proto
    #                                  fields so the server can reject a
    #                                  search that omits them
    #   CONTENT    lesson_title, ... — sent as proto `filters`, and dropped by
    #                                  the agent when they exclude everything
    #
    # One dict rather than two because that is the shape planning.py already
    # produces; the split happens in the client, in one place.
    filters: dict[str, Any] = field(default_factory=dict)
    mode: str = "hybrid"                # "hybrid" | "dense" | "sparse"


@dataclass(slots=True)
class SearchHit:
    chunk_id: str
    score: float
    content: str
    title: str = ""
    page: int = 0
    source: str = ""                    # "sparse", "semantic", "semantic+sparse"
    payload: dict[str, Any] = field(default_factory=dict)

    # Rank within each retrieval leg BEFORE fusion. 0 means that leg did not
    # return this hit at all.
    #
    # Not decoration: "dense #2, sparse #0" and "dense #0, sparse #1" are very
    # different results wearing the same fused score, and telling them apart
    # is the difference between "the sparse leg is dead" and "this query is
    # semantic". The retrieval lab exists mostly to surface this; carrying it
    # into production means the same question is answerable from a log line.
    dense_rank: int = 0
    sparse_rank: int = 0


@dataclass(slots=True)
class SearchResponse:
    hits: list[SearchHit]
    language_used: str
    collection_used: str

    # The user has indexed nothing at all. Distinct from "searched and matched
    # nothing" — it maps to a different reason code and a different message.
    user_has_no_documents: bool = False

    # Chunks the user owns, regardless of filters. Lets a zero-hit result be
    # read correctly: 0 chunks owned is an upload problem, 400 chunks owned
    # and 0 hits is a query or filter problem.
    total_user_chunks: int = 0

    # Content filter keys the SERVER applied. If a key the agent sent is
    # missing here, the server rejected it — which is otherwise
    # indistinguishable from the filter having excluded everything.
    filters_applied: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TitleInfo:
    """One real lesson title, exactly as stored in the payload."""
    title: str
    chunk_count: int = 0


@dataclass(slots=True)
class TitleListing:
    titles: list[TitleInfo] = field(default_factory=list)
    total_chunks: int = 0
    # The server's scan hit its page cap, so this list is incomplete. Worth
    # knowing before concluding a title does not exist.
    truncated: bool = False

    def names(self) -> list[str]:
        return [t.title for t in self.titles]
