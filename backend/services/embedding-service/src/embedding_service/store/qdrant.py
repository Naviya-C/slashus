"""Qdrant access.

THE EFFICIENCY CHANGE: FUSION MOVED SERVER-SIDE
-----------------------------------------------
Previous builds ran the dense leg and the sparse leg as two separate
``query_points`` calls and fused the rankings in Python. That is two network
round trips per search, two result sets serialised over the wire, and a fusion
implementation to maintain.

Qdrant does this natively with `prefetch` + `FusionQuery(Fusion.RRF)`: both
legs execute inside the database, fusion happens where the data already is, and
one response comes back. One round trip, less bytes on the wire, and the
ranking stays adjacent to the index.

What stays on this side is de-duplication (`store.ranking`), which Qdrant has
no notion of, and the ownership filter, which is built here so that no code
path can construct a search without it.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient, models
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from embedding_service.config.settings import QdrantSettings, RetrievalSettings
from embedding_service.domain.models import (
    ChunkPayload,
    SearchHit,
    SearchMode,
    SparseVector,
    TitleInfo,
    TitleListing,
)

log = structlog.get_logger(__name__)

FILTERABLE_KEYS = frozenset(
    {"lesson_title", "lesson_number", "page_number", "block_type", "source_file", "chunk_id"}
)
INTEGER_KEYS = frozenset({"page_number", "lesson_number", "chunk_index", "token_count"})


class QdrantTransportError(RuntimeError):
    """Retryable transport failure."""


def _coerce(key: str, value: str) -> str | int:
    if key in INTEGER_KEYS:
        try:
            return int(value)
        except (TypeError, ValueError):
            log.warning("qdrant.filter_not_integer", key=key, value=value)
    return value


def build_filter(
    *, user_id: str, doc_ids: Sequence[str], content: dict[str, list[str]]
) -> tuple[models.Filter, list[str]]:
    """Ownership is always applied, and is built HERE rather than accepted from
    the caller -- multi-tenant isolation must not depend on every call site
    remembering to pass it."""
    must: list[models.Condition] = [
        models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
    ]
    if doc_ids:
        must.append(models.FieldCondition(key="doc_id", match=models.MatchAny(any=list(doc_ids))))

    applied: list[str] = []
    for key, raw in content.items():
        values = [v for v in raw if v != ""]
        if not values:
            continue
        if key not in FILTERABLE_KEYS:
            log.warning("qdrant.filter_rejected", key=key)
            continue
        coerced = [_coerce(key, v) for v in values]
        must.append(
            models.FieldCondition(key=key, match=models.MatchValue(value=coerced[0]))
            if len(coerced) == 1
            else models.FieldCondition(key=key, match=models.MatchAny(any=coerced))
        )
        applied.append(key)

    return models.Filter(must=must), sorted(applied)


_retry_transport = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.2, max=3.0),
    retry=retry_if_exception_type(QdrantTransportError),
    reraise=True,
)


class QdrantStore:
    def __init__(
        self,
        settings: QdrantSettings,
        retrieval: RetrievalSettings,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        self._cfg = settings
        self._retrieval = retrieval
        self._client = client or AsyncQdrantClient(
            url=settings.endpoint,
            api_key=settings.api_key.get_secret_value() if settings.api_key else None,
            timeout=settings.timeout_seconds,
        )
        self._title_cache: dict[str, tuple[float, TitleListing]] = {}

    @property
    def client(self) -> AsyncQdrantClient:
        return self._client

    # ---------------------------writes---------------------------------

    @_retry_transport
    async def upsert(
        self,
        *,
        collection: str,
        points: Sequence[tuple[str, list[float], SparseVector, ChunkPayload]],
    ) -> int:
        if not points:
            return 0
        structs = [
            models.PointStruct(
                id=point_id,
                vector={
                    self._cfg.dense_vector_name: dense,
                    self._cfg.sparse_vector_name: models.SparseVector(
                        indices=sparse.indices, values=sparse.values
                    ),
                },
                payload=payload.to_qdrant(),
            )
            for point_id, dense, sparse, payload in points
        ]
        try:
            await self._client.upsert(collection_name=collection, points=structs, wait=True)
        except Exception as exc:
            raise QdrantTransportError(str(exc)) from exc
        affected_users = {point[3].user_id for point in points}
        for cache_key in list(self._title_cache):
            if cache_key.startswith(f"{collection}:") and any(
                f":{user_id}:" in cache_key for user_id in affected_users
            ):
                self._title_cache.pop(cache_key, None)
        return len(structs)

    # --------------------------reads-----------------------------------

    @_retry_transport
    async def count_owned(self, *, collection: str, user_id: str, doc_ids: Sequence[str]) -> int:
        flt, _ = build_filter(user_id=user_id, doc_ids=doc_ids, content={})
        try:
            result = await self._client.count(
                collection_name=collection, count_filter=flt, exact=True
            )
        except Exception as exc:
            raise QdrantTransportError(str(exc)) from exc
        return int(result.count)

    @staticmethod
    def _to_hits(points: Any) -> list[SearchHit]:
        hits: list[SearchHit] = []
        known = {"text", "lesson_title", "page_number", "chunk_id", "doc_id", "source_file"}
        for p in points:
            payload = p.payload or {}
            hits.append(
                SearchHit(
                    chunk_id=str(payload.get("chunk_id", p.id)),
                    score=float(p.score),
                    content=str(payload.get("text", "")),
                    title=str(payload.get("lesson_title") or ""),
                    page=int(payload.get("page_number") or 0),
                    doc_id=str(payload.get("doc_id", "")),
                    source=str(payload.get("source_file", "")),
                    extra={
                        k: str(v) for k, v in payload.items() if k not in known and v is not None
                    },
                )
            )
        return hits

    @_retry_transport
    async def hybrid_search(
        self,
        *,
        collection: str,
        dense: list[float] | None,
        sparse: SparseVector | None,
        limit: int,
        conditions: models.Filter,
        mode: SearchMode = SearchMode.HYBRID,
    ) -> list[SearchHit]:
        """One round trip. Both legs and the fusion run inside Qdrant."""
        fetch = max(limit, int(limit * self._retrieval.oversample))

        prefetch: list[models.Prefetch] = []
        if mode in (SearchMode.HYBRID, SearchMode.DENSE) and dense is not None:
            prefetch.append(
                models.Prefetch(
                    query=dense,
                    using=self._cfg.dense_vector_name,
                    filter=conditions,
                    limit=fetch,
                )
            )
        if (
            mode in (SearchMode.HYBRID, SearchMode.SPARSE)
            and sparse is not None
            and not sparse.is_empty()
        ):
            prefetch.append(
                models.Prefetch(
                    query=models.SparseVector(indices=sparse.indices, values=sparse.values),
                    using=self._cfg.sparse_vector_name,
                    filter=conditions,
                    limit=fetch,
                )
            )

        if not prefetch:
            return []

        try:
            if len(prefetch) == 1:

                leg = prefetch[0]
                response = await self._client.query_points(
                    collection_name=collection,
                    query=leg.query,
                    using=leg.using,
                    query_filter=conditions,
                    limit=fetch,
                    with_payload=True,
                )
            else:
                response = await self._client.query_points(
                    collection_name=collection,
                    prefetch=prefetch,
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=fetch,
                    with_payload=True,
                )
        except Exception as exc:
            raise QdrantTransportError(str(exc)) from exc

        return self._to_hits(response.points)

    async def list_titles(
        self, *, collection: str, user_id: str, doc_ids: Sequence[str], limit: int
    ) -> TitleListing:
        """
        Scroll and count distinct lesson titles. TTL-cached: this is an
        O(corpus) scan that the agent may call on any turn.
        """
        
        cache_key = f"{collection}:{user_id}:{','.join(sorted(doc_ids))}"
        ttl = self._retrieval.title_cache_ttl_seconds
        now = time.monotonic()

        if ttl > 0 and (entry := self._title_cache.get(cache_key)):
            cached_at, listing = entry
            if now - cached_at < ttl:
                return listing

        flt, _ = build_filter(user_id=user_id, doc_ids=doc_ids, content={})
        counts: dict[str, int] = {}
        total = 0
        truncated = True
        offset: Any = None

        facet = getattr(self._client, "facet", None)
        if facet is not None:
            try:
                response = await facet(
                    collection_name=collection,
                    key="lesson_title",
                    facet_filter=flt,
                    limit=limit or 10_000,
                    exact=True,
                )
                ordered = sorted(
                    ((str(hit.value), int(hit.count)) for hit in response.hits if hit.value),
                    key=lambda item: (-item[1], item[0]),
                )
                listing = TitleListing(
                    titles=[TitleInfo(title=title, chunk_count=count) for title, count in ordered],
                    total_chunks=sum(count for _, count in ordered),
                    truncated=False,
                )
                if ttl > 0:
                    self._title_cache[cache_key] = (now, listing)
                return listing
            except Exception:
                log.warning("qdrant.title_facet_failed_falling_back", exc_info=True)

        for _ in range(self._retrieval.title_scan_max_pages):
            try:
                points, offset = await self._client.scroll(
                    collection_name=collection,
                    scroll_filter=flt,
                    limit=self._retrieval.title_scan_page_size,
                    offset=offset,
                    with_payload=["lesson_title"],
                    with_vectors=False,
                )
            except Exception as exc:
                raise QdrantTransportError(str(exc)) from exc

            total += len(points)
            for p in points:
                if title := (p.payload or {}).get("lesson_title"):
                    counts[str(title)] = counts.get(str(title), 0) + 1
            if offset is None:
                truncated = False
                break

        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if limit:
            ordered = ordered[:limit]

        listing = TitleListing(
            titles=[TitleInfo(title=t, chunk_count=n) for t, n in ordered],
            total_chunks=total,
            truncated=truncated,
        )
        if ttl > 0:
            self._title_cache[cache_key] = (now, listing)
        return listing

    # ------------------------lifecycle--------------------------------

    async def ping(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except Exception:
            log.warning("qdrant.ping_failed", exc_info=True)
            return False

    async def ensure_collection(self, collection: str, dimensions: int) -> bool:
        """Idempotent. Returns True when it created one.

        Idempotence is what makes this usable as an init container; a version
        that exits non-zero when the collection exists fails loudest on the
        safe, repeatable path.
        """
        exists = await self._client.collection_exists(collection)
        if exists:
            info = await self._client.get_collection(collection)
            vectors = info.config.params.vectors
            dense = vectors.get(self._cfg.dense_vector_name) if isinstance(vectors, dict) else None
            if dense is None or int(dense.size) != dimensions:
                raise RuntimeError(
                    f"collection {collection!r} dense vector mismatch: expected "
                    f"{self._cfg.dense_vector_name!r}/{dimensions}"
                )
            sparse = info.config.params.sparse_vectors or {}
            if self._cfg.sparse_vector_name not in sparse:
                raise RuntimeError(
                    f"collection {collection!r} lacks sparse vector "
                    f"{self._cfg.sparse_vector_name!r}"
                )
            modifier = getattr(sparse[self._cfg.sparse_vector_name], "modifier", None)
            if "idf" not in str(modifier).casefold():
                raise RuntimeError(f"collection {collection!r} sparse vector must use Modifier.IDF")
            log.info("qdrant.collection_exists", collection=collection)

        else:
            await self._client.create_collection(
                collection_name=collection,
                vectors_config={
                    self._cfg.dense_vector_name: models.VectorParams(
                        size=dimensions, distance=models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    self._cfg.sparse_vector_name: models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False),
                        modifier=models.Modifier.IDF,
                    )
                },
            )
        for field, schema in (
            ("user_id", models.PayloadSchemaType.KEYWORD),
            ("doc_id", models.PayloadSchemaType.KEYWORD),
            ("source_file", models.PayloadSchemaType.KEYWORD),
            ("block_type", models.PayloadSchemaType.KEYWORD),
            ("lesson_title", models.PayloadSchemaType.KEYWORD),
            ("page_number", models.PayloadSchemaType.INTEGER),
            ("lesson_number", models.PayloadSchemaType.INTEGER),
            ("chunk_index", models.PayloadSchemaType.INTEGER),
        ):
            await self._client.create_payload_index(
                collection_name=collection, field_name=field, field_schema=schema, wait=True
            )

        log.info("qdrant.collection_created", collection=collection, dimensions=dimensions)
        return not exists

    async def close(self) -> None:
        await self._client.close()
