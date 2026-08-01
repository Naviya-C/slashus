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
"""

from __future__ import annotations

import logging
import os

import grpc

from vectorstore import search_pb2, search_pb2_grpc
from vectorstore.schemas import SearchHit, SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

_MODES = {
    "hybrid": search_pb2.SEARCH_MODE_HYBRID,
    "dense": search_pb2.SEARCH_MODE_DENSE,
    "sparse": search_pb2.SEARCH_MODE_SPARSE,
}

# Generous: a cold embedding-service is still loading BGE-M3, and the first
# search after a deploy legitimately waits. Short enough that a hung service
# surfaces as an error rather than a spinner the user stares at.
_TIMEOUT_SECONDS = 30


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
        doc_ids = request.filters.get("doc_id") or []
        if isinstance(doc_ids, str):
            doc_ids = [doc_ids]

        try:
            resp = self._stub.Search(
                search_pb2.SearchRequest(
                    query=request.query,
                    user_id=user_id,
                    doc_ids=[str(d) for d in doc_ids],
                    limit=request.limit,
                    mode=_MODES.get(request.mode, search_pb2.SEARCH_MODE_HYBRID),
                    language=request.language,
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
            )
            for h in resp.hits
        ]

        if resp.user_has_no_documents:
            # Distinct from "searched and matched nothing" — the user needs a
            # different instruction. Carried on the response rather than
            # inferred from an empty hit list.
            logger.info("user %s has no indexed chunks", user_id)

        return SearchResponse(
            hits=hits,
            language_used=resp.language_used,
            collection_used=resp.collection_used,
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
