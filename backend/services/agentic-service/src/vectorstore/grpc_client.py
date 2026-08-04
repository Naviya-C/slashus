"""
src/vectorstore/grpc_client.py
==============================

Vector search over gRPC, replacing the in-process Qdrant backend.

WHAT THIS REMOVED
-----------------
agentic-service used to open its own QdrantClient, load its own BGE-M3
(~2.2 GB), and read its own copy of sparse_vocab.json. That meant:

  * two copies of the same model on an 8 GB VM already running Kafka
  * two views of a vocab file that ingest appends to — this reader's copy went
    stale the moment a new document introduced a term, and the only symptom
    was slightly worse sparse retrieval, with no error anywhere
  * the ownership filter applied by the caller, so a bug here could return
    another user's chunks

Now embedding-service owns all three and enforces the filter itself.

WHAT STAYED HERE
----------------
The retrieval LOOP — retries, query rewriting, budget escalation, BM25 fusion,
diversification. Those are policy and belong with the agent that tunes them.
This client is a thin transport.

WHAT CHANGED IN v2
------------------
Content filters now actually reach the server.

Before, this client read `user_id` and `doc_id` out of the filter dict and
DROPPED everything else on the floor. The retrieval agent built a
`lesson_title` filter, logged it, and searched as though it had applied — the
filter existed in the agent's world and nowhere else. Any conclusion drawn
about whether filtering helped was measuring nothing.

`list_titles` is also new. It returns the real stored titles so the agent can
match against them instead of asking a model to invent one.
"""

from __future__ import annotations

import logging
import os

import grpc

from vectorstore import search_pb2, search_pb2_grpc
from vectorstore.schemas import (
    SearchHit,
    SearchRequest,
    SearchResponse,
    TitleInfo,
    TitleListing,
)

logger = logging.getLogger(__name__)

_MODES = {
    "hybrid": search_pb2.SEARCH_MODE_HYBRID,
    "dense": search_pb2.SEARCH_MODE_DENSE,
    "sparse": search_pb2.SEARCH_MODE_SPARSE,
}

# Ownership keys are promoted to typed proto fields; everything else in the
# filter dict is a content filter and goes in the map. Named here rather than
# inline so the two places that care cannot disagree.
_OWNERSHIP_KEYS = ("user_id", "doc_id")

# Generous: a cold embedding-service is still loading BGE-M3, and the first
# search after a deploy legitimately waits. Short enough that a hung service
# surfaces as an error rather than a spinner the user stares at.
_TIMEOUT_SECONDS = 30

# ListTitles scans rather than searches, and runs once per session rather than
# once per query, so it gets its own shorter budget. A slow title scan should
# degrade title matching, not the whole request.
_TITLES_TIMEOUT_SECONDS = 15


def _as_list(value) -> list[str]:
    """Normalise a filter value to a list of strings.

    A bare string is a one-element list, not an iterable of characters — the
    obvious loop over `value` would send ['අ', 'ත', 'ී', ...] and match
    nothing.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v is not None and str(v) != ""]
    return [str(value)] if str(value) != "" else []


class GrpcVectorClient:
    """Talks to embedding-service. Satisfies the same interface the
    in-process MCP client did, so the retrieval agent is unchanged."""

    def __init__(self, target: str | None = None) -> None:
        self._target = target or os.getenv("EMBEDDING_GRPC_URL", "embedding-service:50051")
        # A channel is lazy and reconnects on its own, so building it at
        # construction costs nothing and survives embedding-service restarts
        # without needing to rebuild here.
        self._channel = grpc.insecure_channel(
            self._target,
            options=[
                ("grpc.max_receive_message_length", 16 * 1024 * 1024),
                # Keepalives so a silently dropped connection is detected
                # rather than discovered on the next user request.
                ("grpc.keepalive_time_ms", 30_000),
                ("grpc.keepalive_timeout_ms", 10_000),
            ],
        )
        self._stub = search_pb2_grpc.VectorSearchStub(self._channel)
        logger.info("vector search over gRPC -> %s", self._target)

    # ------------------------------------------------------------------

    def search(self, request: SearchRequest) -> SearchResponse:
        # user_id comes through filters because that is the shape the
        # retrieval agent already builds. Promoted to a typed proto field so
        # it cannot be forgotten — the server rejects a search without it.
        user_id = str(request.filters.get("user_id", ""))
        doc_ids = _as_list(request.filters.get("doc_id"))

        content = {
            key: search_pb2.FilterValues(values=_as_list(value))
            for key, value in request.filters.items()
            if key not in _OWNERSHIP_KEYS and _as_list(value)
        }

        try:
            resp = self._stub.Search(
                search_pb2.SearchRequest(
                    query=request.query,
                    user_id=user_id,
                    doc_ids=doc_ids,
                    limit=request.limit,
                    mode=_MODES.get(request.mode, search_pb2.SEARCH_MODE_HYBRID),
                    language=request.language,
                    filters=content,
                ),
                timeout=_TIMEOUT_SECONDS,
            )
        except grpc.RpcError as exc:
            # Return empty rather than raising. The retrieval agent's loop
            # already handles an empty result, and the orchestrator turns that
            # into a user-facing message. Raising here would surface a gRPC
            # stack trace as a 500 for what is a recoverable dependency
            # outage.
            logger.error("search failed (%s): %s", exc.code(), exc.details())
            return SearchResponse(hits=[], language_used=request.language,
                                  collection_used="")

        hits = [
            SearchHit(
                chunk_id=h.chunk_id,
                score=h.score,
                content=h.content,
                title=h.title,
                page=h.page,
                source=h.source,
                payload={"doc_id": h.doc_id, **dict(h.extra)},
                dense_rank=h.dense_rank,
                sparse_rank=h.sparse_rank,
            )
            for h in resp.hits
        ]

        requested = set(content)
        ignored = requested - set(resp.filters_applied)
        if ignored:
            # The server refused a key — almost always one that is not in the
            # payload schema. Silence here would let the agent believe it
            # narrowed a search it did not narrow.
            logger.warning("server ignored filter keys %s", sorted(ignored))

        if resp.user_has_no_documents:
            # Distinct from "searched and matched nothing" — the user needs a
            # different instruction. Carried on the response rather than
            # inferred from an empty hit list.
            logger.info("user %s has no indexed chunks", user_id)

        return SearchResponse(
            hits=hits,
            language_used=resp.language_used,
            collection_used=resp.collection_used,
            user_has_no_documents=resp.user_has_no_documents,
            total_user_chunks=resp.total_user_chunks,
            filters_applied=list(resp.filters_applied),
        )

    # ------------------------------------------------------------------

    def list_titles(self, user_id: str, doc_ids: list[str] | None = None,
                    limit: int = 0) -> TitleListing:
        """The exact lesson titles stored for this user.

        Returns an empty listing on any failure rather than raising. Title
        matching is an optimisation: without it retrieval falls back to
        searching the whole corpus, which is worse but works. A dead title
        scan must not take chat down with it.
        """
        try:
            resp = self._stub.ListTitles(
                search_pb2.ListTitlesRequest(
                    user_id=str(user_id),
                    doc_ids=[str(d) for d in (doc_ids or [])],
                    limit=limit,
                ),
                timeout=_TITLES_TIMEOUT_SECONDS,
            )
        except grpc.RpcError as exc:
            logger.warning("list_titles failed (%s): %s", exc.code(), exc.details())
            return TitleListing()

        if resp.truncated:
            logger.warning(
                "title listing truncated for user %s — a title missing from "
                "this list may still exist", user_id,
            )

        return TitleListing(
            titles=[TitleInfo(title=t.title, chunk_count=t.chunk_count)
                    for t in resp.titles],
            total_chunks=resp.total_chunks,
            truncated=resp.truncated,
        )

    # ------------------------------------------------------------------

    def languages(self) -> list[str]:
        """Kept for interface compatibility. Language routing moved into
        embedding-service, which owns the collections."""
        return ["si"]

    def health(self) -> tuple[bool, str]:
        """Probes the gRPC port specifically.

        embedding-service's HTTP /health can pass while its gRPC thread is
        dead — that combination is what makes chat hang with nothing in the
        logs. Used by scripts/check.py.
        """
        try:
            resp = self._stub.Health(search_pb2.HealthRequest(), timeout=5)
            return resp.ready, f"{resp.detail} (vocab {resp.vocab_hash})"
        except grpc.RpcError as exc:
            return False, f"{exc.code()}: {exc.details()}"

    def close(self) -> None:
        self._channel.close()


def build_vector_client() -> GrpcVectorClient:
    """Composition root for vector search.

    Was a choice between an in-process and an HTTP MCP client. Now there is
    one implementation: embedding-service owns the store, and nothing else
    talks to Qdrant.
    """
    return GrpcVectorClient()
