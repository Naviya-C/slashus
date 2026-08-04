"""
tools/retrieval.py
==================

Deterministic retrieval execution. The agent decides WHAT to search; these
decide nothing.

Everything here was already correct in the previous version and is unchanged
in substance — hybrid search over gRPC, RRF in embedding-service, BM25 fusion
and diversification locally. What changed is who calls it: the keywords, the
lesson title, the filters and the budget now arrive from an LLM-produced plan
instead of being assembled by Python.

The one piece of policy that stays HERE, and must: ownership. `user_id` is
injected by the registry from the authenticated session, and the filter is
built below rather than accepted from the plan. A plan is model output; model
output has read untrusted textbook text; and Qdrant has no concept of
ownership of its own.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from core.retrieval.ranking import diversify, fuse_bm25
from core.config import settings
from tools.base import Tool, ToolError, ToolRegistry, clamp_int
from vectorstore import SearchRequest

logger = logging.getLogger(__name__)

# Payload keys a PLAN may filter on. The same allowlist reasoning as
# embedding-service, enforced here too so a bad plan never becomes a wire
# request: a key that is not in the payload matches zero points and Qdrant
# reports that as success, which reads as "no relevant documents" while the
# material sits right there.
#
# `lesson_title` is allowed here because the plan gets it from the real title
# list (see list_lesson_titles), not from a model inventing a string.
_PLANNABLE_FILTERS = frozenset({"lesson_title", "page_number", "block_type"})

_MAX_BUDGET = settings.max_chunk_budget
_OVERFETCH = settings.overfetch_factor


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

    def hybrid_search(*, user_id: UUID, session_id: str, query: str,
                      lesson_title: str = "", filters: dict | None = None,
                      budget: int = 12, doc_ids: list | None = None,
                      title_as: str = "boost") -> dict[str, Any]:
        """Dense + sparse + RRF (embedding-service), then BM25 fusion and
        diversification locally."""
        if not str(query or "").strip():
            raise ToolError("query is empty")

        budget = clamp_int(budget, 12, 1, _MAX_BUDGET)

        # Ownership, built here and never from the plan.
        applied: dict[str, Any] = {"user_id": str(user_id)}
        if doc_ids:
            applied["doc_id"] = [str(d) for d in doc_ids]

        for key, value in (filters or {}).items():
            if key in _PLANNABLE_FILTERS and value not in (None, ""):
                applied[key] = value
            elif key not in _PLANNABLE_FILTERS:
                logger.info("plan proposed non-filterable key %r; ignored", key)

        if lesson_title and title_as == "filter":
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

        # A content filter that matched nothing excludes EVERYTHING, and
        # Qdrant reports that as a successful empty result. Recovery is here
        # rather than left to the agent because it costs one extra call and
        # the alternative is a confident "your documents don't cover this"
        # about material that is sitting in the index.
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

        if lesson_title and title_as == "boost" and hits:
            # Reorders, does not exclude. A wrong title costs a little ranking
            # instead of the whole answer, and chunks with no title at all
            # survive — a filter drops those permanently.
            matched = [h for h in hits if h.title == lesson_title]
            if matched:
                hits = matched + [h for h in hits if h.title != lesson_title]

        if hits:
            hits = fuse_bm25(query, hits)
        hits = diversify(hits, budget)

        return {
            "chunks": [_chunk_dict(h) for h in hits],
            "user_has_no_documents": False,
            "total_user_chunks": response.total_user_chunks,
            "filters_applied": list(response.filters_applied),
        }

    def list_lesson_titles(*, user_id: UUID, session_id: str,
                           doc_ids: list | None = None) -> dict[str, Any]:
        """The EXACT stored lesson titles, so the agent picks a real one.

        This is what makes lesson-title planning possible at all. Asked to
        produce a title from nothing, a model returns something plausible —
        'අතීතයේ කතාව' where the corpus holds 'අතීතයෙන්  කතාවක්', different
        inflection and a double space from PDF extraction. Exact-match
        filtering on that excludes an entire lesson and reports success.
        """
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
            "filters": "optional: page_number, block_type",
            "budget": "how many chunks to return, 1-40",
            "title_as": "'boost' to prefer the lesson, 'filter' to require it",
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
