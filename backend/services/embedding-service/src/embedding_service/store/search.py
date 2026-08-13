"""Search use-case.

Thin, because fusion moved into Qdrant. What remains here is the part that
cannot live in the database: telling "this student has uploaded nothing" apart
from "we searched and found nothing", and de-duplicating the fused result.
"""

from __future__ import annotations

import structlog

from embedding_service.config.settings import Settings
from embedding_service.domain.models import (
    SearchMode,
    SearchResult,
    TitleListing,
)
from embedding_service.observability.metrics import (
    SEARCH_DURATION,
    SEARCH_EMPTY,
    SEARCH_HITS,
)
from embedding_service.store.qdrant import build_filter
from embedding_service.store.ranking import diversify, weighted_fuse

log = structlog.get_logger(__name__)


class SearchService:
    def __init__(self, *, settings: Settings, store, dense, sparse) -> None:
        self._settings = settings
        self._store = store
        self._dense = dense
        self._sparse = sparse

    @property
    def _collection(self) -> str:
        return self._settings.qdrant.collection

    async def search(
        self,
        *,
        query: str,
        user_id: str,
        doc_ids: list[str],
        limit: int,
        filters: dict[str, list[str]],
        mode: SearchMode = SearchMode.HYBRID,
        language: str = "si",
    ) -> SearchResult:
        cfg = self._settings.retrieval
        collection = self._collection

        with SEARCH_DURATION.labels(mode=mode.value).time():
            # An empty corpus and an empty result set need different messages
            # downstream, and an empty hit list alone cannot distinguish them.
            total_owned = await self._store.count_owned(
                collection=collection, user_id=user_id, doc_ids=doc_ids
            )
            if total_owned == 0:
                SEARCH_EMPTY.labels(reason="no_documents").inc()
                return SearchResult(
                    collection_used=collection,
                    language_used=language,
                    user_has_no_documents=True,
                )

            content_filters = dict(filters)
            try:
                title_confidence = float(
                    (content_filters.pop("_title_confidence", ["0"]) or ["0"])[0]
                )
            except (TypeError, ValueError):
                title_confidence = 0.0
            selected_titles = content_filters.get("lesson_title", [])
            use_title_strategy = bool(
                selected_titles and title_confidence >= cfg.title_confidence_threshold
            )
            if not use_title_strategy:
                content_filters.pop("lesson_title", None)

            conditions, applied = build_filter(
                user_id=user_id, doc_ids=doc_ids, content=content_filters
            )

            dense_vector = (
                await self._dense.embed_query(query)
                if mode in (SearchMode.HYBRID, SearchMode.DENSE)
                else None
            )
            sparse_vector = (
                self._sparse.encode(query)
                if mode in (SearchMode.HYBRID, SearchMode.SPARSE)
                else None
            )

            if use_title_strategy:
                import asyncio

                global_filters = dict(content_filters)
                global_filters.pop("lesson_title", None)
                global_conditions, _ = build_filter(
                    user_id=user_id, doc_ids=doc_ids, content=global_filters
                )
                title_hits, global_hits = await asyncio.gather(
                    self._store.hybrid_search(
                        collection=collection,
                        dense=dense_vector,
                        sparse=sparse_vector,
                        limit=max(limit, int(limit * cfg.oversample)),
                        conditions=conditions,
                        mode=mode,
                    ),
                    self._store.hybrid_search(
                        collection=collection,
                        dense=dense_vector,
                        sparse=sparse_vector,
                        limit=max(limit, int(limit * cfg.oversample)),
                        conditions=global_conditions,
                        mode=mode,
                    ),
                )
                fused = weighted_fuse(
                    title_hits,
                    global_hits,
                    title_weight=cfg.title_weight,
                    global_weight=cfg.global_weight,
                    limit=max(limit, int(limit * cfg.oversample)),
                )
                applied = sorted({*applied, "title_weighted_strategy"})
            else:
                fused = await self._store.hybrid_search(
                    collection=collection,
                    dense=dense_vector,
                    sparse=sparse_vector,
                    limit=limit,
                    conditions=conditions,
                    mode=mode,
                )
            hits = diversify(fused, limit, threshold=cfg.diversity_threshold)

        SEARCH_HITS.labels(mode=mode.value).observe(len(hits))
        if not hits:
            SEARCH_EMPTY.labels(reason="no_matches").inc()

        log.info(
            "search.completed",
            user_id=user_id,
            mode=mode.value,
            fused=len(fused),
            returned=len(hits),
            deduplicated=len(fused) - len(hits),
            total_owned=total_owned,
            filters_applied=applied,
        )

        return SearchResult(
            hits=hits,
            collection_used=collection,
            language_used=language,
            total_user_chunks=total_owned,
            filters_applied=applied,
        )

    async def list_titles(
        self, *, user_id: str, doc_ids: list[str], limit: int = 0
    ) -> TitleListing:
        return await self._store.list_titles(
            collection=self._collection, user_id=user_id, doc_ids=doc_ids, limit=limit
        )
