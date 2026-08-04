from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from core.retrieval.ranking import diversify, fuse_bm25
from core.config import settings
from tools.base import Tool, ToolError, ToolRegistry, clamp_int
from vectorstore import SearchRequest

logger = logging.getLogger(__name__)

_PLANNABLE_FILTERS = frozenset({"lesson_title", "page_number", "block_type"})

_MAX_BUDGET = settings.max_chunk_budget
_OVERFETCH = settings.overfetch_factor
_TITLE_FILTER_AT = 0.80
_TITLE_WEIGHTS = ((0.50, 3.0), (0.40, 1.5))


def _chunk_dict(hit) -> dict[str, Any]:
    return {
        "chunk_id": hit.chunk_id,
        "content": hit.content,
        "title": hit.title,
        "page": hit.page,
        "score": hit.score,
        "source": hit.source,
        "dense_rank": hit.dense_rank,
        "sparse_rank": hit.sparse_rank,
    }


def register_retrieval_tools(registry: ToolRegistry, vectors) -> None:

    def _weight_for(confidence: float) -> float:
        for threshold, weight in _TITLE_WEIGHTS:
            if confidence >= threshold:
                return weight
        return 1.0

    def hybrid_search(*, user_id: UUID, session_id: str, query: str,
                      lesson_title: str = "", title_confidence: float = 0.0,
                      filters: dict | None = None,
                      budget: int = 12, doc_ids: list | None = None,
                      title_as: str = "auto") -> dict[str, Any]:

        if not str(query or "").strip():
            raise ToolError("query is empty")

        budget = clamp_int(budget, 12, 1, _MAX_BUDGET)

        applied: dict[str, Any] = {"user_id": str(user_id)}
        if doc_ids:
            applied["doc_id"] = [str(d) for d in doc_ids]

        for key, value in (filters or {}).items():
            if key in _PLANNABLE_FILTERS and value not in (None, ""):
                applied[key] = value
            elif key not in _PLANNABLE_FILTERS:
                logger.info("plan proposed non-filterable key %r; ignored", key)

        as_filter = (
            title_as == "filter"
            or (title_as == "auto" and title_confidence >= _TITLE_FILTER_AT)
        )
        if lesson_title and as_filter:
            applied["lesson_title"] = lesson_title

        response = vectors.search(SearchRequest(
            query=query,
            language="si",
            limit=max(budget, int(budget * _OVERFETCH)),
            filters=applied,
            mode="hybrid",
        ))

        hits = response.hits

        if response.user_has_no_documents:
            return {"chunks": [], "user_has_no_documents": True,
                    "total_user_chunks": 0, "filters_applied": []}

        content = [k for k in applied if k not in ("user_id", "doc_id")]
        if not hits and content:
            logger.warning("zero hits under %s — retrying without them", content)
            for key in content:
                applied.pop(key, None)
            response = vectors.search(SearchRequest(
                query=query, language="si",
                limit=max(budget, int(budget * _OVERFETCH)),
                filters=applied, mode="hybrid",
            ))
            hits = response.hits

        if hits:
            hits = fuse_bm25(query, hits)

        weight = _weight_for(title_confidence)
        if lesson_title and not as_filter and hits and weight > 1.0:
            for h in hits:
                if h.title == lesson_title:
                    h.score *= weight
            hits = sorted(hits, key=lambda h: h.score, reverse=True)

        hits = diversify(hits, budget)

        logger.info(
            "search %r -> %d hits (dense/sparse=%d/%d) title=%r conf=%.2f "
            "mode=%s filters=%s",
            query, len(hits),
            sum(1 for h in hits if h.dense_rank),
            sum(1 for h in hits if h.sparse_rank),
            lesson_title, title_confidence,
            "filter" if as_filter else f"weight x{weight}",
            list(response.filters_applied),
        )

        return {
            "chunks": [_chunk_dict(h) for h in hits],
            "user_has_no_documents": False,
            "total_user_chunks": response.total_user_chunks,
            "filters_applied": list(response.filters_applied),
        }

    def list_lesson_titles(*, user_id: UUID, session_id: str,
                           doc_ids: list | None = None) -> dict[str, Any]:
        listing = vectors.list_titles(str(user_id),
                                      [str(d) for d in (doc_ids or [])])
        return {
            "titles": [{"title": t.title, "chunks": t.chunk_count}
                       for t in listing.titles],
            "total_chunks": listing.total_chunks,
            "truncated": listing.truncated,
        }

    registry.add(Tool(
        name="hybrid_search",
        description=(
            "Search the student's own documents. Runs dense (BGE-M3) and "
            "sparse retrieval, fuses with RRF, then BM25 and de-duplication"),
        args={
            "query": "what to search for — the SUBJECT, not the request wrapper",
            "lesson_title": "an EXACT title from list_lesson_titles, or empty",
            "title_confidence": "0.0-1.0; >=0.8 restricts the search to that "
                                "lesson, >=0.4 ranks it higher, below is ignored",
            "filters": "optional: page_number, block_type",
            "budget": "how many chunks to return, 1-40",
            "title_as": "'auto' grades on title_confidence; 'filter' or "
                        "'boost' force the mode",
        },
        run=hybrid_search,
    ))

    registry.add(Tool(
        name="list_lesson_titles",
        description=(
            "List the exact lesson titles in the student's documents. Call "
            "this BEFORE setting lesson_title, and only ever use a title "
            "returned by it"),
        args={"doc_ids": "optional: restrict to these documents"},
        run=list_lesson_titles,
    ))