# adapters/sparse_encoder.py  
"""
Sinhala-aware sparse encoder. Emits raw term frequencies -- Qdrant computes IDF
server-side (Modifier.IDF), so the vocab can grow without re-encoding old points.

The vocab is a BUILD ARTIFACT the agent service must load identically. Drift
between index-time and query-time vocab = silent retrieval garbage.
"""
from __future__ import annotations
import json, re
from collections import Counter
from pathlib import Path

_TOKEN_RE = re.compile(r"[\u0D80-\u0DFF]+|[a-zA-Z]+|\d+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2]


class SinhalaSparseEncoder:
    def __init__(self, vocab_path: str | Path, frozen: bool = False):
        self._path = Path(vocab_path)
        self._frozen = frozen
        self._vocab: dict[str, int] = (
            json.loads(self._path.read_text(encoding="utf-8")) if self._path.exists() else {}
        )

    def _index(self, token: str) -> int | None:
        if token in self._vocab:
            return self._vocab[token]
        if self._frozen:
            return None                     
        idx = len(self._vocab)
        self._vocab[token] = idx
        return idx

    def encode_documents(self, texts):
        out = []
        for t in texts:
            counts = Counter(tokenize(t))
            pairs = [(self._index(tok), float(n)) for tok, n in counts.items()]
            pairs = [(i, v) for i, v in pairs if i is not None]
            pairs.sort()
            out.append(([i for i, _ in pairs], [v for _, v in pairs]))
        return out

    def encode_query(self, text: str):
        counts = Counter(tokenize(text))
        pairs = sorted((self._vocab[tok], float(n)) for tok, n in counts.items() if tok in self._vocab)
        return [i for i, _ in pairs], [v for _, v in pairs]

    def save(self) -> None:
        """Persist the vocab atomically.

        write_text truncates the file before writing. A crash mid-write — or
        two writers overlapping — leaves a truncated JSON file that fails to
        parse on next load, and the encoder silently starts from an empty
        vocab. Every subsequent query then matches nothing on the sparse leg,
        with no error anywhere.

        Write to a temp file in the same directory, then rename. Rename is
        atomic on POSIX, so a reader sees either the old file or the new one,
        never a half-written one.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._vocab, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)