"""
src/core/retrieval/bm25.py
==========================

Okapi BM25, computed locally over a retrieved candidate pool.

WHY LOCALLY, AND WHY THIS IS NOT A WORKAROUND
---------------------------------------------
The sparse leg of hybrid search is NOT BM25 today. It sends raw query term
frequencies to Qdrant and the score is a dot product against whatever weights
ingestion wrote. That gives, at best, TF-IDF — and only if the collection was
created with Qdrant's IDF modifier.

Real BM25 needs two things a dot product cannot express:

  * k1 saturation      — the tenth occurrence of a term must count for far
                         less than the first. Without it, a chunk that repeats
                         one word outranks a chunk that actually answers the
                         question.
  * b length norm      — a long chunk contains more of everything. Without
                         normalization, long chunks win on size alone.

Both are functions of DOCUMENT statistics (term frequency within the doc, doc
length vs corpus average), which means the document-side weights must be
written at INGEST time. That is embedding-service's job, and changing it means
re-indexing the whole corpus.

This module gets true BM25 without that, by scoring the retrieved chunk TEXTS
directly — we already have them in memory. It runs as a third retrieval signal
fused alongside dense and sparse, costs nothing (no API, no model), and needs
no re-indexing.

THE HONEST LIMITATION
---------------------
IDF is computed over the candidate pool, not the corpus. Every candidate
already matched the query, so document frequencies are inflated relative to
the true corpus and discriminative terms look less rare than they are. This is
the standard trade for candidate-pool rescoring and it works well in practice
— but it means BM25 here is a RE-RANKING signal, not a retrieval signal. It
can reorder what dense and sparse found; it cannot surface something they
both missed.

For corpus-wide BM25, ingestion must write BM25-weighted document vectors. See
the note at the bottom of this file.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Standard Okapi parameters. k1 controls how quickly term frequency saturates;
# b controls how strongly length is normalized (0 = not at all, 1 = fully).
# These values are the field default and a sensible starting point for mixed
# Sinhala/English text.
DEFAULT_K1 = 1.5
DEFAULT_B = 0.75

# MUST match embedding-service's tokenizer in
# embedding_service/adapter/sparse_encoder.py. They are in different services
# now, so nothing enforces it — a divergence here degrades BM25 fusion
# silently, with no error on either side.
_TOKEN_RE = re.compile(r"[\u0D80-\u0DFF]+|[a-zA-Z]+|\d+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2]


@dataclass(slots=True)
class ScoredDoc:
    index: int
    score: float


class BM25:
    """Okapi BM25 over a fixed set of documents.

    Built per-query over the candidate pool, so there is no index to maintain
    and no staleness: the statistics always describe exactly the documents
    being ranked.
    """

    def __init__(self, documents: list[str], *, k1: float = DEFAULT_K1,
                 b: float = DEFAULT_B) -> None:
        self._k1 = k1
        self._b = b

        self._tokenized = [tokenize(d) for d in documents]
        self._lengths = [len(t) for t in self._tokenized]
        self._term_freqs = [Counter(t) for t in self._tokenized]

        total = sum(self._lengths)
        self._n = len(documents)
        # Guard against an empty pool: avgdl of 0 makes the length
        # normalization term divide by zero.
        self._avgdl = (total / self._n) if self._n else 0.0

        self._idf = self._build_idf()

    def _build_idf(self) -> dict[str, float]:
        """Robertson-Sparck-Jones IDF with the +1 smoothing.

        The +1 inside the log keeps IDF non-negative. Without it, a term
        appearing in more than half the pool gets a NEGATIVE weight, and a
        document is then penalised for containing a query term — which is
        never what you want when the pool is small and terms are common by
        construction.
        """
        df: Counter[str] = Counter()
        for tokens in self._tokenized:
            df.update(set(tokens))

        return {
            term: math.log(1.0 + (self._n - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }

    def score(self, query: str) -> list[ScoredDoc]:
        """Score every document against the query, highest first."""
        if not self._n or not self._avgdl:
            return []

        query_terms = tokenize(query)
        if not query_terms:
            return []

        # Query terms deduplicated: BM25 scores each DISTINCT query term once.
        # Counting repeats would let a user double a term's weight simply by
        # repeating it, which is not what the model intends.
        unique_terms = set(query_terms)

        results: list[ScoredDoc] = []
        for i, tf in enumerate(self._term_freqs):
            score = 0.0
            length_ratio = self._lengths[i] / self._avgdl

            for term in unique_terms:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                idf = self._idf.get(term, 0.0)
                # The saturation term: as freq grows, the numerator grows
                # linearly while the denominator grows too, so the whole
                # expression approaches (k1 + 1) rather than growing forever.
                numerator = freq * (self._k1 + 1)
                denominator = freq + self._k1 * (1 - self._b + self._b * length_ratio)
                score += idf * numerator / denominator

            if score > 0:
                results.append(ScoredDoc(index=i, score=score))

        results.sort(key=lambda d: d.score, reverse=True)
        return results


def rank(query: str, documents: list[str], *, k1: float = DEFAULT_K1,
         b: float = DEFAULT_B) -> list[ScoredDoc]:
    """Convenience wrapper — build and score in one call."""
    return BM25(documents, k1=k1, b=b).score(query)


# ---------------------------------------------------------------------------
# FOR CORPUS-WIDE BM25 (requires re-indexing)
# ---------------------------------------------------------------------------
# embedding-service would need to write BM25-weighted sparse vectors at ingest
# instead of raw counts:
#
#     weight(t, D) = tf(t,D) * (k1 + 1)
#                    / (tf(t,D) + k1 * (1 - b + b * |D| / avgdl))
#
# with |D| the chunk's token count and avgdl the corpus average, computed in a
# first pass over all chunks.
#
# The query side then sends 1.0 per distinct query term (NOT counts — the
# saturation is already baked into the document weights), and Qdrant's
# Modifier.IDF supplies the IDF from real corpus statistics.
#
# That combination is exact Okapi BM25 with corpus-wide IDF, and it would
# replace this module as a RETRIEVAL signal rather than a reranking one.
