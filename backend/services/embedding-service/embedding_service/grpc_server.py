"""
embedding_service/grpc_server.py
================================

Serves vector search over gRPC. embedding-service owns Qdrant, BGE-M3, and the
sparse vocab; this is the only way anything else reaches them.

What this does NOT do: the retrieval loop. No retries, no query rewriting, no
budget escalation, no BM25 fusion, no diversification. Those are retrieval
POLICY and live in agentic-service's retrieval agent, where they change as
prompts are tuned. This is a fast, stateless "given a query and a filter,
return ranked hits" — so tuning retrieval never means redeploying the service
that also runs the ingestion consumer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from concurrent import futures
from pathlib import Path

import grpc
from qdrant_client import models

from embedding_service import search_pb2, search_pb2_grpc
from embedding_service.config import load_env

log = logging.getLogger(__name__)

# RRF constant. 60 is the value from the original paper and the de facto
# default; it damps the contribution of low-ranked results without needing
# per-query tuning.
_RRF_K = 60
# Dense/sparse weighting. Dense carries more because BGE-M3 handles Sinhala
# morphology far better than term matching does; sparse is there to catch the
# exact-term cases dense paraphrases away.
_W_DENSE, _W_SPARSE = 0.7, 0.3


class VectorSearchServicer(search_pb2_grpc.VectorSearchServicer):
    def __init__(self, deps) -> None:
        self._deps = deps
        cfg = load_env()
        self._collection = cfg["QDRANT_COLLECTION"]
        self._vocab_path = cfg["SPARSE_VOCAB_PATH"]
        # Computed once at startup and returned by Health. If agentic-service
        # ever caches anything vocab-derived, comparing hashes turns silent
        # drift into a visible mismatch.
        self._vocab_hash = self._hash_vocab()

    # ------------------------------------------------------------------

    def _hash_vocab(self) -> str:
        try:
            raw = Path(self._vocab_path).read_bytes()
            return hashlib.sha256(raw).hexdigest()[:12]
        except Exception:
            return "unavailable"

    @staticmethod
    def _build_filter(user_id: str, doc_ids: list[str]) -> models.Filter:
        """Ownership filter, enforced HERE rather than trusted from the caller.

        This service owns Qdrant, so it decides who can read what. Qdrant has
        no concept of ownership of its own — a query without user_id returns
        every user's chunks.
        """
        must: list[models.Condition] = [
            models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
        ]
        if doc_ids:
            # MatchAny, not a loop of MatchValue: several MatchValue conditions
            # on the same key AND together and match nothing — and Qdrant
            # returns an empty result rather than an error, so it looks like a
            # relevance problem.
            must.append(
                models.FieldCondition(key="doc_id", match=models.MatchAny(any=list(doc_ids)))
            )
        return models.Filter(must=must)

    # ------------------------------------------------------------------

    def Search(self, request, context):  # noqa: N802  (gRPC naming)
        limit = request.limit or 10
        query_filter = self._build_filter(request.user_id, list(request.doc_ids))

        # Cheap existence check before embedding anything. Distinguishes "this
        # user has uploaded nothing" from "the search ran and matched nothing",
        # which need different messages in the UI.
        try:
            total = self._deps.client.count(
                collection_name=self._collection,
                count_filter=query_filter,
                exact=True,
            ).count
        except Exception:
            log.exception("count failed; continuing")
            total = -1

        if total == 0:
            return search_pb2.SearchResponse(
                hits=[], collection_used=self._collection,
                language_used=request.language or "si",
                user_has_no_documents=True,
            )

        mode = request.mode
        dense_hits: list = []
        sparse_hits: list = []

        if mode in (search_pb2.SEARCH_MODE_HYBRID, search_pb2.SEARCH_MODE_DENSE):
            dense_hits = self._dense(request.query, limit, query_filter)
        if mode in (search_pb2.SEARCH_MODE_HYBRID, search_pb2.SEARCH_MODE_SPARSE):
            sparse_hits = self._sparse(request.query, limit, query_filter)

        fused = self._fuse(dense_hits, sparse_hits, limit)

        return search_pb2.SearchResponse(
            hits=fused,
            collection_used=self._collection,
            language_used=request.language or "si",
            user_has_no_documents=False,
        )

    # ------------------------------------------------------------------

    def _dense(self, query: str, limit: int, flt) -> list[tuple[str, float, dict]]:
        # .embed() is the QUERY side — it prefixes "query: " before encoding,
        # while embed_documents() does not. That asymmetry is the reason the
        # proto makes purpose an explicit enum: the two are one method call
        # apart and mixing them degrades retrieval with no error anywhere.
        vector = self._deps.dense.embed(query)
        res = self._deps.client.query_points(
            collection_name=self._collection,
            query=vector,
            using="dense",
            limit=limit,
            query_filter=flt,
            with_payload=True,
        )
        return [(str(p.id), float(p.score), p.payload or {}) for p in res.points]

    def _sparse(self, query: str, limit: int, flt) -> list[tuple[str, float, dict]]:
        indices, values = self._deps.sparse.encode_query(query)
        if not indices:
            # No query term is in the vocab. Not an error — dense still
            # covers it, and an empty sparse leg just means RRF fuses one list.
            return []
        res = self._deps.client.query_points(
            collection_name=self._collection,
            query=models.SparseVector(indices=indices, values=values),
            using="sparse",
            limit=limit,
            query_filter=flt,
            with_payload=True,
        )
        return [(str(p.id), float(p.score), p.payload or {}) for p in res.points]

    # ------------------------------------------------------------------

    def _fuse(self, dense, sparse, limit) -> list:
        """Reciprocal rank fusion.

        Ranks, not scores: dense cosine similarity and sparse dot products
        live on different scales, so adding them lets whichever happens to be
        numerically larger dominate — and which one that is varies per query.
        """
        scores: dict[str, float] = {}
        payloads: dict[str, dict] = {}
        sources: dict[str, set[str]] = {}

        for weight, hits, label in (
            (_W_DENSE, dense, "semantic"),
            (_W_SPARSE, sparse, "bm25"),
        ):
            for rank, (pid, _score, payload) in enumerate(hits, 1):
                scores[pid] = scores.get(pid, 0.0) + weight / (_RRF_K + rank)
                payloads.setdefault(pid, payload)
                sources.setdefault(pid, set()).add(label)

        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]

        out = []
        for pid, score in ordered:
            payload = payloads[pid]
            # Everything not promoted to a typed field goes in `extra`, as
            # strings. A map keeps payload additions from requiring a stub
            # regeneration in two services.
            known = {"text", "lesson_title", "page_number", "chunk_id", "doc_id"}
            extra = {
                k: str(v) for k, v in payload.items()
                if k not in known and v is not None
            }
            out.append(search_pb2.Hit(
                chunk_id=str(payload.get("chunk_id", pid)),
                score=float(score),
                content=str(payload.get("text", "")),
                title=str(payload.get("lesson_title", "")),
                page=int(payload.get("page_number") or 0),
                doc_id=str(payload.get("doc_id", "")),
                source="+".join(sorted(sources[pid])),
                extra=extra,
            ))
        return out

    # ------------------------------------------------------------------

    def Embed(self, request, context):  # noqa: N802
        texts = list(request.texts)
        if request.purpose == search_pb2.EMBED_PURPOSE_DOCUMENT:
            dense = self._deps.dense.embed_documents(texts)
            sparse = self._deps.sparse.encode_documents(texts)
        else:
            dense = [self._deps.dense.embed(t) for t in texts]
            sparse = [self._deps.sparse.encode_query(t) for t in texts]

        return search_pb2.EmbedResponse(
            dense=[search_pb2.DenseVector(values=v) for v in dense],
            sparse=[
                search_pb2.SparseVector(indices=i, values=v) for i, v in sparse
            ],
        )

    def Health(self, request, context):  # noqa: N802
        return search_pb2.HealthResponse(
            ready=True, detail="ok", vocab_hash=self._vocab_hash
        )


# ---------------------------------------------------------------------------

def serve(deps, port: int = 50051, max_workers: int = 4) -> grpc.Server:
    """Start the gRPC server on a background thread.

    max_workers=4 rather than 1: a single worker serializes concurrent
    searches, so two users asking at once means the second waits for the
    first's full embed + two Qdrant round trips. Four is ample at this scale
    and costs nothing when idle.
    """
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            # Chunk text is the bulk of a response — 10 hits at ~1200 chars of
            # Sinhala. Default 4 MB is enough, but being explicit means a
            # future larger limit is a deliberate change rather than a
            # surprise truncation.
            ("grpc.max_send_message_length", 16 * 1024 * 1024),
            ("grpc.max_receive_message_length", 16 * 1024 * 1024),
        ],
    )
    search_pb2_grpc.add_VectorSearchServicer_to_server(
        VectorSearchServicer(deps), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    log.info("gRPC search server listening on :%d", port)
    return server


def serve_forever(deps, port: int = 50051) -> None:
    """Blocking variant, for running on a dedicated thread."""
    server = serve(deps, port)
    server.wait_for_termination()
