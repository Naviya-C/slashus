r"""Sinhala-aware sparse encoder.

WHY NOT fastembed's ``Qdrant/bm25``
-----------------------------------
That model's tokenizer is ``re.sub(r"[^\w]", " ", text)``. Sinhala combining
vowel signs are Unicode categories Mn/Mc and ZWJ is Cf -- none of which match
``\w`` -- so every Sinhala word is split at every vowel sign. Verified against
fastembed 0.8.0:

    'ශ්‍රී ලංකාවේ ඉතිහාසය පිළිබඳ පාඩම'
    -> ['ශ','ර','ල','ක','ව','ඉත','හ','සය','ප','ළ','බඳ','ප','ඩම']

Five words become thirteen fragments, and on a small corpus roughly half the
resulting vocabulary is single consonants -- characters that appear in nearly
every Sinhala document. Under BM25 those carry almost no IDF, so the sparse leg
stops discriminating and contributes noise instead of lexical signal.

The fragmentation is at least deterministic, so exact-phrase queries still
match. It is not total breakage. But for a Sinhala-first product it throws away
most of the value of having a sparse leg at all.

WHAT THIS DOES INSTEAD
----------------------
Keeps everything that makes the fastembed approach good -- hashed indices, no
vocabulary state, IDF supplied by Qdrant's ``Modifier.IDF`` -- and replaces
only the tokenizer with one that treats Sinhala grapheme runs as words.

Being stateless is the property that matters operationally: ``index =
hash(token)`` is a pure function, so every replica agrees, restarts change
nothing, and ingest order is irrelevant. A vocabulary-file encoder has none of
those and forces a single-writer deployment.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

import mmh3

from embedding_service.domain.models import SparseVector

_TOKEN_RE = re.compile(r"[\u0D80-\u0DFF\u200D]+|[a-zA-Z]+|\d+")
_ZWJ = "\u200d"


def tokenize(text: str, *, min_length: int = 2) -> list[str]:
    """Tokenize mixed Sinhala/English/numeric text."""
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text.lower()):
        token = raw.strip(_ZWJ)
        if len(token) >= min_length:
            tokens.append(token)
    return tokens


class SinhalaSparseEncoder:
    """Stateless, deterministic, hashed BM25-style sparse encoder."""

    __slots__ = ("_buckets", "_k1", "_min_length", "_seed")

    def __init__(
        self,
        *,
        num_buckets: int = 1 << 20,
        seed: int = 0,
        min_token_length: int = 2,
        k1: float = 1.2,
    ) -> None:
        self._buckets = num_buckets
        self._seed = seed
        self._min_length = min_token_length
        self._k1 = k1

    @property
    def num_buckets(self) -> int:
        return self._buckets

    def _bucket(self, token: str) -> int:
        return mmh3.hash(token, self._seed, signed=False) % self._buckets

    def encode(self, text: str) -> SparseVector:
        counts: dict[int, float] = {}
        for token in tokenize(text, min_length=self._min_length):
            bucket = self._bucket(token)
            counts[bucket] = counts.get(bucket, 0.0) + 1.0

        if not counts:
            return SparseVector()

        indices = sorted(counts)
        values = [(counts[i] * (self._k1 + 1.0)) / (counts[i] + self._k1) for i in indices]
        return SparseVector(indices=indices, values=values)

    def encode_batch(self, texts: Sequence[str] | Iterable[str]) -> list[SparseVector]:
        return [self.encode(t) for t in texts]

    encode_documents = encode_batch
    encode_query = encode
