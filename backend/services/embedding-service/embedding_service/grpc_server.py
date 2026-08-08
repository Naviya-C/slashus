"""
Serves vector search over gRPC. embedding-service owns Qdrant, BGE-M3, and the
sparse vocab; this is the only way anything else reaches them.
"""

from __future__ import annotations

import hashlib 
import logging
from collections import Counter
from concurrent import futures
from pathlib import Path

import grpc
from qdrant_client import models

from embedding_service import search_pb2, search_pb2_grpc
from embedding_service.config import load_env

log = logging.getLogger(__name__)

_RRF_K = 60
_W_DENSE, _W_SPARSE = 0.7, 0.3

_FILTERABLE = frozenset({
    "lesson_title",
    "page_number",
    "block_type",
    "source_file",
    "chunk_id",
})

_INT_KEYS = frozenset({"page_number", "chunk_index", "token_count"})
_TITLE_SCAN_PAGES = 20
_TITLE_SCAN_PAGE_SIZE = 1000


def _coerce(key: str, value: str):
    """
    ---Wire string -> the type stored in the payload.---
    gRPC filter values arrive as strings But Qdrant stores page_number as an integer,
    Therefore use convert them.
    """
    if key in _INT_KEYS:
        try:
            return int(value)
        except (TypeError, ValueError):
            log.warning("filter %s=%r is not an integer", key, value)
    return value

class VectorSearchServicer(search_pb2_grpc.VectorSearchServicer):
    def __init__(self, deps) -> None:
        self._deps = deps
        cfg = load_env()
        self._collection = cfg["QDRANT_COLLECTION"]
        self._vocab_path = cfg["SPARSE_VOCAB_PATH"]
        self._vocab_hash = self._hash_vocab()

    def _hash_vocab(self) -> str:
        try:
            raw = Path(self._vocab_path).read_bytes()
            return hashlib.sha256(raw).hexdigest()[:12]
        except Exception:
            return "unavailable"

    @staticmethod
    def _ownership(user_id: str, doc_ids: list[str]) -> list[models.Condition]:
        must: list[models.Condition] = [
            models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
        ]
        if doc_ids:
            must.append(
                models.FieldCondition(key="doc_id", match=models.MatchAny(any=list(doc_ids)))
            )
        return must

    @staticmethod
    def _content(filters) -> tuple[list[models.Condition], list[str]]:
        conditions: list[models.Condition] = []
        applied: list[str] = []

        for key, holder in filters.items():
            values = [v for v in holder.values if v != ""]
            if not values:
                continue
            if key not in _FILTERABLE:
                log.warning("ignoring non-filterable key %r", key)
                continue

            coerced = [_coerce(key, v) for v in values]
            if len(coerced) == 1:
                conditions.append(models.FieldCondition(
                    key=key, match=models.MatchValue(value=coerced[0])))
            else:
                conditions.append(models.FieldCondition(
                    key=key, match=models.MatchAny(any=coerced)))
            applied.append(key)

        return conditions, sorted(applied)


    def Search(self, request, context):  
        if not request.user_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "user_id is required")

        limit = request.limit or 10
        owner = self._ownership(request.user_id, list(request.doc_ids))
        content, applied = self._content(request.filters)

        try:
            total = self._deps.client.count(
                collection_name=self._collection,
                count_filter=models.Filter(must=owner),
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
                total_user_chunks=0,
            )

        query_filter = models.Filter(must=owner + content)

        mode = request.mode
        dense_hits: list = []
        sparse_hits: list = []

        if mode in (search_pb2.SEARCH_MODE_HYBRID, search_pb2.SEARCH_MODE_DENSE):
            dense_hits = self._dense(request.query, limit, query_filter)
        if mode in (search_pb2.SEARCH_MODE_HYBRID, search_pb2.SEARCH_MODE_SPARSE):
            sparse_hits = self._sparse(request.query, limit, query_filter)

        fused = self._fuse(dense_hits, sparse_hits, limit)

        if not fused and applied:
            log.info(
                "zero hits under content filters %s for user %s (%d chunks owned)",
                applied, request.user_id, total,
            )

        return search_pb2.SearchResponse(
            hits=fused,
            collection_used=self._collection,
            language_used=request.language or "si",
            user_has_no_documents=False,
            total_user_chunks=max(total, 0),
            filters_applied=applied,
        )

    def ListTitles(self, request, context):  
        if not request.user_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "user_id is required")

        flt = models.Filter(must=self._ownership(request.user_id, list(request.doc_ids)))

        counts: Counter = Counter()
        total = 0
        truncated = False
        offset = None

        try:
            for _ in range(_TITLE_SCAN_PAGES):
                points, offset = self._deps.client.scroll(
                    collection_name=self._collection,
                    scroll_filter=flt,
                    limit=_TITLE_SCAN_PAGE_SIZE,
                    offset=offset,
                    with_payload=["lesson_title"],
                    with_vectors=False,
                )
                total += len(points)
                for p in points:
                    title = (p.payload or {}).get("lesson_title")
                    if title:
                        counts[str(title)] += 1
                if offset is None:
                    break
            else:
                truncated = True
        except Exception:
            log.exception("ListTitles scan failed")
            context.abort(grpc.StatusCode.INTERNAL, "title scan failed")

        ordered = counts.most_common()
        if request.limit:
            ordered = ordered[: request.limit]

        log.info("ListTitles: %d titles over %d chunks for user %s%s",
                 len(counts), total, request.user_id,
                 " (truncated)" if truncated else "")

        return search_pb2.ListTitlesResponse(
            titles=[search_pb2.TitleInfo(title=t, chunk_count=n) for t, n in ordered],
            total_chunks=total,
            truncated=truncated,
        )

    def _dense(self, query: str, limit: int, flt) -> list[tuple[str, float, dict]]:
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

    def _fuse(self, dense, sparse, limit) -> list:
        scores: dict[str, float] = {}
        payloads: dict[str, dict] = {}
        sources: dict[str, set] = {}
        ranks: dict[str, dict] = {}

        for weight, hits, label in (
            (_W_DENSE, dense, "semantic"),
            (_W_SPARSE, sparse, "sparse"),
        ):
            for rank, (pid, _score, payload) in enumerate(hits, 1):
                scores[pid] = scores.get(pid, 0.0) + weight / (_RRF_K + rank)
                payloads.setdefault(pid, payload)
                sources.setdefault(pid, set()).add(label)
                ranks.setdefault(pid, {})[label] = rank

        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]

        out = []
        for pid, score in ordered:
            payload = payloads[pid]
            known = {"text", "lesson_title", "page_number", "chunk_id", "doc_id"}
            extra = {
                k: str(v) for k, v in payload.items()
                if k not in known and v is not None
            }
            out.append(search_pb2.Hit(
                chunk_id=str(payload.get("chunk_id", pid)),
                score=float(score),
                content=str(payload.get("text", "")),
                title=str(payload.get("lesson_title") or ""),
                page=int(payload.get("page_number") or 0),
                doc_id=str(payload.get("doc_id", "")),
                source="+".join(sorted(sources[pid])),
                extra=extra,
                dense_rank=ranks[pid].get("semantic", 0),
                sparse_rank=ranks[pid].get("sparse", 0),
            ))
        return out

    def Embed(self, request, context):  
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


def serve(deps, port: int = 50051, max_workers: int = 4) -> grpc.Server:
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
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
