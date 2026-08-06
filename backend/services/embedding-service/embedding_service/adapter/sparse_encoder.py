# embedding_service/adapter/sparse_encoder.py
"""
Sinhala-aware sparse encoder. Emits raw term frequencies -- Qdrant computes IDF
server-side (Modifier.IDF), so the vocab can grow without re-encoding old points.

The vocab is a BUILD ARTIFACT. Drift between index-time and query-time vocab =
silent retrieval garbage.

THREAD SAFETY
-------------
This object is shared by every thread in the process: the Kafka consumer on the
document side, and the gRPC worker pool on the query side -- which also reaches
encode_documents via Embed(purpose=DOCUMENT). Two rules follow.

  * WRITES ARE LOCKED. `_index` is a read-then-write on len(self._vocab). Two
    threads interleaving both read len() as N and both assign index N to
    different tokens, so two terms collide on one dimension and every sparse
    vector written afterwards is subtly wrong -- with no error anywhere, and no
    way to detect it short of re-ingesting the corpus.

  * READS ARE NOT LOCKED, deliberately. The vocab is INSERT-ONLY: no key is ever
    removed and no index is ever reassigned, so a concurrent lookup either finds
    a token or does not, and both answers are correct. Locking encode_query
    would serialise every search behind ingest encoding -- the exact latency
    coupling that consolidating into one process was supposed to avoid.

SAVE BATCHING
-------------
save() used to run once per chunk, so a 300-chunk book rewrote a growing JSON
file 300 times. It now no-ops until `save_every` NEW terms have accumulated.
Call save(force=True) when the consumer goes idle and on shutdown, or the tail
of the vocab is lost on a crash.

The serialise-and-write happens under the lock. That blocks encode_documents for
a few tens of milliseconds, but only once per `save_every` new terms -- rare
after the first document -- and it never blocks a query.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections import Counter
from pathlib import Path

log = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[\u0D80-\u0DFF]+|[a-zA-Z]+|\d+")

DEFAULT_SAVE_EVERY = 256


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2]


class SinhalaSparseEncoder:
    def __init__(
        self,
        vocab_path: str | Path,
        frozen: bool = False,
        save_every: int = DEFAULT_SAVE_EVERY,
    ):
        self._path = Path(vocab_path)
        self._frozen = frozen
        self._save_every = save_every
        self._lock = threading.Lock()
        self._pending = 0
        self._vocab: dict[str, int] = (
            json.loads(self._path.read_text(encoding="utf-8"))
            if self._path.exists()
            else {}
        )
        log.info("sparse vocab loaded: %d terms", len(self._vocab))

    # ------------------------------------------------------------------
    # writes -- caller MUST hold self._lock
    # ------------------------------------------------------------------

    def _index_locked(self, token: str) -> int | None:
        idx = self._vocab.get(token)
        if idx is not None:
            return idx
        if self._frozen:
            return None
        idx = len(self._vocab)
        self._vocab[token] = idx
        self._pending += 1
        return idx

    def encode_documents(self, texts) -> list[tuple[list[int], list[float]]]:
        out: list[tuple[list[int], list[float]]] = []
        with self._lock:
            for t in texts:
                pairs: list[tuple[int, float]] = []
                for tok, n in Counter(tokenize(t)).items():
                    idx = self._index_locked(tok)
                    if idx is not None:
                        pairs.append((idx, float(n)))
                pairs.sort()
                out.append(([i for i, _ in pairs], [v for _, v in pairs]))
        return out

    # ------------------------------------------------------------------
    # reads -- lock-free by design, see module docstring
    # ------------------------------------------------------------------

    def encode_query(self, text: str) -> tuple[list[int], list[float]]:
        vocab = self._vocab
        pairs: list[tuple[int, float]] = []
        for tok, n in Counter(tokenize(text)).items():
            idx = vocab.get(tok)
            if idx is not None:
                pairs.append((idx, float(n)))
        pairs.sort()
        return [i for i, _ in pairs], [v for _, v in pairs]

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def save(self, force: bool = False) -> bool:
        with self._lock:
            if self._pending == 0:
                return False
            if not force and self._pending < self._save_every:
                return False

            payload = json.dumps(self._vocab, ensure_ascii=False)
            new_terms, total = self._pending, len(self._vocab)
            self._pending = 0

            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(self._path)

        log.info("sparse vocab saved: %d terms (+%d new)", total, new_terms)
        return True

    def __len__(self) -> int:
        return len(self._vocab)