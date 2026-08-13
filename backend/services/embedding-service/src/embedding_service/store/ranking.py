"""Post-fusion ranking: near-duplicate removal.

Fusion itself happens SERVER-SIDE in Qdrant (see ``store.qdrant``), which is
one round trip instead of two and keeps the ranking next to the data. What
Qdrant does not do is de-duplicate, and textbook PDFs repeat running headers,
boilerplate and page furniture across many pages -- so an undiversified top-10
is frequently the same paragraph several times, filling the agent's context
without adding information.
"""

from __future__ import annotations

from embedding_service.domain.models import SearchHit
from embedding_service.encoders.sparse import tokenize


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def diversify(hits: list[SearchHit], limit: int, *, threshold: float = 0.8) -> list[SearchHit]:
    """Drop near-duplicates, preserving relevance order."""
    out: list[SearchHit] = []
    kept: list[set[str]] = []

    for hit in hits:
        tokens = set(tokenize(hit.content))
        if not tokens:
            continue
        if any(_jaccard(tokens, prev) >= threshold for prev in kept):
            continue
        out.append(hit)
        kept.append(tokens)
        if len(out) >= limit:
            break

    return out


def weighted_fuse(
    title_hits: list[SearchHit],
    global_hits: list[SearchHit],
    *,
    title_weight: float,
    global_weight: float,
    limit: int,
    rank_constant: int = 60,
) -> list[SearchHit]:
    """Weighted reciprocal-rank fusion across title-aware and global branches."""
    scores: dict[str, float] = {}
    values: dict[str, SearchHit] = {}
    for hits, weight in ((title_hits, title_weight), (global_hits, global_weight)):
        for rank, hit in enumerate(hits, start=1):
            values.setdefault(hit.chunk_id, hit)
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + weight / (rank_constant + rank)
    ordered = sorted(scores, key=lambda key: (-scores[key], key))[:limit]
    return [values[key].model_copy(update={"score": scores[key]}) for key in ordered]
