"""
src/agents/retrieval/ranking.py
===============================

Post-retrieval ranking: BM25 fusion, LLM reranking, and diversity selection.

Three stages, in increasing cost:

    fuse_bm25    free, local, always on
    rerank       one LLM call, off by default
    diversify    free, local, always on

The ordering matters. BM25 fusion runs before reranking so the LLM sees an
already-improved ordering, and diversification runs last so it operates on
final relevance rather than discarding a chunk the reranker promoted.
"""

from __future__ import annotations

import logging
from string import Template

from core.llm import LLMClient
from core.retrieval.bm25 import BM25, tokenize
from vectorstore import SearchHit

logger = logging.getLogger(__name__)

_RRF_K = 60

_RERANK = Template(
    """Reorder these chunks most- to least-relevant to the query. Do not answer.

QUERY: $query
CHUNKS:
$chunks

Return ONLY JSON: {"ranking": ["id1", "id2", ...]}
"""
)


# ---------------------------------------------------------------------------
# BM25 fusion
# ---------------------------------------------------------------------------

def fuse_bm25(query: str, hits: list[SearchHit], *, weight: float = 0.4) -> list[SearchHit]:
    if len(hits) <= 1:
        return hits

    ranked = BM25([h.content for h in hits]).score(query)
    if not ranked:
        # No query term appears in any candidate. Nothing to fuse; the
        # incoming ordering stands on its own.
        return hits

    # The incoming order IS a ranking — position 0 is rank 1.
    fused: dict[str, float] = {
        h.chunk_id: (1 - weight) / (_RRF_K + rank)
        for rank, h in enumerate(hits, 1)
    }
    for rank, doc in enumerate(ranked, 1):
        cid = hits[doc.index].chunk_id
        fused[cid] = fused.get(cid, 0.0) + weight / (_RRF_K + rank)

    out = sorted(hits, key=lambda h: fused[h.chunk_id], reverse=True)
    for h in out:
        h.score = fused[h.chunk_id]
        if "bm25" not in h.source:
            h.source += "+bm25"

    logger.debug("bm25 fusion reordered %d hits", len(out))
    return out


# ---------------------------------------------------------------------------
# LLM reranking
# ---------------------------------------------------------------------------

class Reranker:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        if len(hits) <= 1:
            return hits

        listing = "\n\n".join(f"[ID: {h.chunk_id}] {h.content[:1000]}" for h in hits)
        try:
            data = self._llm.generate_json(_RERANK.substitute(query=query, chunks=listing))
            order = [str(x) for x in data.get("ranking", [])]
        except Exception:
            # Silent degradation: the caller paid for a rerank that did not
            # happen, and nothing in the response says so. ERROR rather than
            # WARNING for exactly that reason.
            logger.exception("rerank failed; keeping incoming order")
            return hits

        by_id = {h.chunk_id: h for h in hits}
        out = [by_id[i] for i in order if i in by_id]
        # Anything the model omitted is appended, not dropped — a truncated
        # ranking must not silently delete candidates.
        seen = {h.chunk_id for h in out}
        out.extend(h for h in hits if h.chunk_id not in seen)
        return out


# ---------------------------------------------------------------------------
# Diversity
# ---------------------------------------------------------------------------

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def diversify(hits: list[SearchHit], limit: int, *,
              redundancy_threshold: float = 0.75) -> list[SearchHit]:
    """Select up to `limit` hits, skipping near-duplicates.

    The previous implementation hashed normalized content and skipped EXACT
    matches. That misses the case that actually occurs: overlapping chunks
    from a sliding window, sharing 80% of their text but differing at the
    edges. Those hash differently, both survive, the LLM receives the same
    passage twice, and the effective context budget silently halves.

    Token-set Jaccard catches it. Deliberately not embedding-based MMR:
    embedding every candidate costs a forward pass each, and windowed overlap
    is lexical by construction — set overlap is both cheaper and more precise
    for this specific problem.
    """
    out: list[SearchHit] = []
    kept: list[set[str]] = []

    for h in hits:
        tokens = set(tokenize(h.content))
        if not tokens:
            continue
        if any(_jaccard(tokens, prev) >= redundancy_threshold for prev in kept):
            logger.debug("dropping near-duplicate chunk %s", h.chunk_id)
            continue

        out.append(h)
        kept.append(tokens)
        if len(out) >= limit:
            break

    return out
