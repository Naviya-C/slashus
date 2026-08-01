"""Vector-database registry: which Qdrant database serves which language.

THIS is the scaling point for multi-language. Today only Sinhala is indexed;
as English and other languages are added, each gets its own Qdrant collection
(and possibly its own cluster). The retrieval flow detects the query language
and this registry maps it to the right database descriptor. The MCP layer then
routes the search there.

Add a language = add one entry here (via env or code). No agent code changes.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VectorDBDescriptor:
    """Everything the MCP server needs to reach ONE Qdrant database."""

    language: str                 # "si", "en", ...
    url: str
    api_key: str | None
    collection: str
    dense_vector: str = "dense"
    sparse_vector: str = "sparse"
    sparse_vocab_path: str | None = None   # per-language frozen vocab
    embedding_model: str = "BAAI/bge-m3"   # per-language embedder (may differ)


def _load_from_env() -> dict[str, VectorDBDescriptor]:
    """Load DB descriptors from env.

    Simple single-DB (current Sinhala) via QDRANT_URL/QDRANT_COLLECTION, or
    multi-DB via VECTOR_DBS_JSON (a JSON list of descriptor dicts). The JSON
    form is how you scale: one object per language.
    """
    raw = os.getenv("VECTOR_DBS_JSON")
    if raw:
        entries = json.loads(raw)
        return {
            e["language"]: VectorDBDescriptor(
                language=e["language"],
                url=e["url"],
                api_key=e.get("api_key"),
                collection=e["collection"],
                dense_vector=e.get("dense_vector", "dense"),
                sparse_vector=e.get("sparse_vector", "sparse"),
                sparse_vocab_path=e.get("sparse_vocab_path"),
                embedding_model=e.get("embedding_model", "BAAI/bge-m3"),
            )
            for e in entries
        }

    # Fallback: single Sinhala DB from the flat env vars (current setup).
    url = os.getenv("QDRANT_URL") or os.getenv("QDRANT_CLUSTER_ENDPOINT") or "http://localhost:6333"
    return {
        "si": VectorDBDescriptor(
            language="si",
            url=url,
            api_key=os.getenv("QDRANT_API_KEY") or os.getenv("QDRANT_CLUSTER_API"),
            collection=os.getenv("QDRANT_COLLECTION", "sinhala_books_v2"),
            sparse_vocab_path=os.getenv("SPARSE_VOCAB_PATH"),
        )
    }


class VectorDBRegistry:
    def __init__(self, descriptors: dict[str, VectorDBDescriptor] | None = None) -> None:
        self._dbs = descriptors if descriptors is not None else _load_from_env()

    @property
    def languages(self) -> list[str]:
        return sorted(self._dbs)

    def has(self, language: str) -> bool:
        return language in self._dbs

    def get(self, language: str) -> VectorDBDescriptor:
        if language in self._dbs:
            return self._dbs[language]
        # Fall back to the first DB (usually Sinhala) so an unknown language
        # still searches *something* rather than failing hard.
        return next(iter(self._dbs.values()))


def primary() -> VectorDBDescriptor:
    """The default database.

    Preflight needs a direct Qdrant handle for a cheap count, which sits
    below the MCP routing layer. Single-language today; when more are added
    this should take a language argument.
    """
    reg = VectorDBRegistry()
    langs = reg.languages
    if not langs:
        raise RuntimeError("no vector databases configured")
    return reg.get("si" if "si" in langs else langs[0])
