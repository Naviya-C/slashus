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
_TITLE_TIERS = ((0.80, 1.0, 0.45), (0.50, 0.7, 0.7), (0.40, 0.4, 1.0))

_RRF_K = 60


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

    def _tier_for(confidence: float) -> tuple[float, float] | None:
        """(title leg weight, general leg weight), or None to skip the leg."""
        for threshold, w_title, w_general in _TITLE_TIERS:
            if confidence >= threshold:
                return w_title, w_general
        return None

    def _rrf(legs: list[tuple[float, list]], limit: int) -> list:
        scores: dict[str, float] = {}
        best: dict[str, Any] = {}
        for weight, hits in legs:
            for rank, hit in enumerate(hits, 1):
                scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + weight / (_RRF_K + rank)
                best.setdefault(hit.chunk_id, hit)

        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        out = []
        for chunk_id, score in ordered:
            hit = best[chunk_id]
            hit.score = score
            out.append(hit)
        return out

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

        as_filter = title_as == "filter"
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

        tier = _tier_for(title_confidence) if lesson_title else None
        title_hits: list = []

        if tier and not as_filter:
            w_title, w_general = tier
            title_response = vectors.search(SearchRequest(
                query=query, language="si",
                limit=max(budget, int(budget * _OVERFETCH)),
                filters={**{k: v for k, v in applied.items()
                            if k in ("user_id", "doc_id")},
                         "lesson_title": lesson_title},
                mode="hybrid",
            ))
            title_hits = title_response.hits

            if title_hits:
                title_hits = fuse_bm25(query, title_hits)
                hits = _rrf([(w_general, hits), (w_title, title_hits)],
                            max(budget, int(budget * _OVERFETCH)))
            else:
                logger.info("title leg returned nothing for %r", lesson_title)

        hits = diversify(hits, budget)

        logger.info(
            "search %r -> %d hits (dense/sparse=%d/%d) title=%r conf=%.2f "
            "mode=%s title_leg=%d filters=%s",
            query, len(hits),
            sum(1 for h in hits if h.dense_rank),
            sum(1 for h in hits if h.sparse_rank),
            lesson_title, title_confidence,
            "filter" if as_filter else ("rrf" if tier else "none"),
            len(title_hits),
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
            "sparse retrieval plus an optional lesson-scoped leg, fuses them "
            "with RRF, then BM25 and de-duplication"),
        args={
            "query": "what to search for — the SUBJECT, not the request wrapper",
            "lesson_title": "an EXACT title from list_lesson_titles, or empty",
            "title_confidence": "0.0-1.0; >=0.4 runs a second search restricted "
                                "to that lesson and fuses it in, weighted by "
                                "confidence. Below 0.4 the title is ignored",
            "filters": "optional: page_number, block_type",
            "budget": "how many chunks to return, 1-40",
            "title_as": "'auto' grades on title_confidence; 'filter' forces a "
                        "hard filter",
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