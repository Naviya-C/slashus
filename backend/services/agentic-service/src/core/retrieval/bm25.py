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

"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


DEFAULT_K1 = 1.5
DEFAULT_B = 0.75


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
        self._avgdl = (total / self._n) if self._n else 0.0

        self._idf = self._build_idf()

    def _build_idf(self) -> dict[str, float]:
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



