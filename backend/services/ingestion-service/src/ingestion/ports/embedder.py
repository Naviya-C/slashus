"""
ports/embedder.py
=================

PURPOSE
-------
The seam between the pipeline and whatever produces dense vectors. Ingest embeds
chunks; search embeds the query. Both go through THIS interface, so the embedding
model (Gemini today, something else tomorrow) is one adapter swap, and tests use
a fake -- no API calls.

THE CONTRACT
------------
    embed_documents(texts) -> list[list[float]]   # for chunks at ingest
    embed_query(text)      -> list[float]         # for the user's search query

Two methods on purpose: retrieval models embed a document and a query
DIFFERENTLY (asymmetric task types). Keeping them separate makes callers use the
right one. This only covers the DENSE vector; BM25 sparse retrieval is unchanged.
"""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...