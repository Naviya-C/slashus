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

WHAT MOVED HERE IN v2
---------------------
Two things, both because they need the store and nothing else does:

  * CONTENT FILTERS. The caller can now pass lesson_title / page_number and
    have them applied server-side. Previously only user_id and doc_ids reached
    Qdrant, so the retrieval agent built content filters that were silently
    discarded in transit — retrieval behaved as though they were never set.

  * ListTitles. The exact stored lesson titles for a user. Retrieval used to
    ask an LLM to produce a title and filtered on the result; the model has
    never seen the corpus, so it produced a plausible title rather than a real
    one and the filter matched zero chunks. Handing back the real strings
    turns that into a closed-set choice.

The POLICY around both still lives in agentic-service. This server applies a
filter and reports which keys it applied; deciding what to do when a filter
excludes everything is the caller's problem, because the answer depends on the
query and this service does not see the query's intent.
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

# RRF constant. 60 is the value from the original paper and the de facto
# default; it damps the contribution of low-ranked results without needing
# per-query tuning.
_RRF_K = 60
# Dense/sparse weighting. Dense carries more because BGE-M3 handles Sinhala
# morphology far better than term matching does; sparse is there to catch the
# exact-term cases dense paraphrases away.
_W_DENSE, _W_SPARSE = 0.7, 0.3

# Payload keys a caller may filter on. An allowlist rather than "anything the
# caller sends", for two reasons:
#
#   * A key that is not in the payload is not an error in Qdrant. It matches
#     zero points and comes back as a successful empty result, which reads as
#     "no relevant documents" while the material sits right there. `lesson_no`
#     is the live example: query understanding emits it, ingest never writes
#     it, and filtering on it wipes out every hit.
#   * Filtering on an unindexed key is a full scan.
#
# `user_id` and `doc_id` are deliberately absent: they arrive as typed request
# fields and are applied unconditionally, so a caller cannot weaken ownership
# by sending them here.
_FILTERABLE = frozenset({
    "lesson_title",
    "page_number",
    "block_type",
    "source_file",
    "chunk_id",
})

# Payload keys that hold integers. A filter value arrives as a string on the
# wire (one type for every key), and MatchValue("42") does not match the
# integer 42 — it matches nothing, silently.
_INT_KEYS = frozenset({"page_number", "chunk_index", "token_count"})

# Cap on the ListTitles scan. A user with a very large corpus should not be
# able to make this walk every point on a UI-triggered call.
_TITLE_SCAN_PAGES = 20
_TITLE_SCAN_PAGE_SIZE = 1000


def _coerce(key: str, value: str):
    """Wire string -> the type stored in the payload."""
    if key in _INT_KEYS:
        try:
            return int(value)
        except (TypeError, ValueError):
            # Leave it as a string rather than dropping the condition. A
            # dropped filter widens the search silently; a filter that matches
            # nothing is visible in filters_applied and recoverable by the
            # caller.
            log.warning("filter %s=%r is not an integer", key, value)
    return value


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
    def _ownership(user_id: str, doc_ids: list[str]) -> list[models.Condition]:
        """Ownership conditions, built HERE rather than trusted from the caller.

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
        return must

    @staticmethod
    def _content(filters) -> tuple[list[models.Condition], list[str]]:
        """Content conditions from the request map, plus the keys applied.

        Returns the applied keys so the response can echo them. Without that
        the caller cannot tell "your filter excluded everything" from "the
        server ignored your filter" — both look like zero hits.
        """
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

    # ------------------------------------------------------------------

    def Search(self, request, context):  # noqa: N802  (gRPC naming)
        if not request.user_id:
            # Refuse rather than default. A search with no user_id would match
            # the entire collection across every account.
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "user_id is required")

        limit = request.limit or 10
        owner = self._ownership(request.user_id, list(request.doc_ids))
        content, applied = self._content(request.filters)

        # Cheap existence check before embedding anything, and deliberately
        # WITHOUT the content filters: it answers "has this user uploaded
        # anything", which is a different question from "does anything match".
        # Counting with the content filters applied would report
        # user_has_no_documents for a user whose only mistake was a bad
        # lesson_title, and the UI would tell them to upload a file they
        # already uploaded.
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
            # Worth a log line of its own. This is the shape of the failure
            # that reads as a relevance problem and is not one.
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

    # ------------------------------------------------------------------

    def ListTitles(self, request, context):  # noqa: N802
        """Distinct lesson titles for a user — the EXACT stored strings.

        These are what a filter must match character for character, including
        any double spaces PDF extraction left behind. Handing them to the
        caller is the whole point: a title an LLM invents almost never matches
        one, and the resulting filter excludes an entire lesson while
        reporting success.

        Counts come along because they are free from the same scan, and they
        answer "is this lesson one paragraph or forty".
        """
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
                    # Payload projection, not with_payload=True: the full
                    # payload includes chunk text, and pulling 20k chunks of
                    # Sinhala across the wire to count titles would be absurd.
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
                title=str(payload.get("lesson_title") or ""),
                page=int(payload.get("page_number") or 0),
                doc_id=str(payload.get("doc_id", "")),
                source="+".join(sorted(sources[pid])),
                extra=extra,
                # 0 means "this leg did not return it". proto3 cannot
                # distinguish unset from zero on a scalar, and rank 0 does not
                # exist, so zero is unambiguous here.
                dense_rank=ranks[pid].get("semantic", 0),
                sparse_rank=ranks[pid].get("sparse", 0),
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
