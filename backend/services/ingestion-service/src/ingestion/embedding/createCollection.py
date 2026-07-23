"""
embedding/createCollection.py
=============================

One-time setup for a collection: vectors config + payload indexes.

Run as a module from the repo root so imports resolve the same way they do
everywhere else in the package:

    python -m src.ingestion.embedding.createCollection

Re-running is safe: an existing collection is left alone rather than
overwritten, so this cannot silently destroy an indexed corpus.
"""

from __future__ import annotations

# Absolute import, matching every other module in the package. The bare
# `from config import load_env` only resolved when the working directory
# happened to be src/ingestion/, and raised ModuleNotFoundError otherwise.
from src.ingestion.config import load_env

from qdrant_client import QdrantClient, models

environ = load_env()

NAME = environ.get("QDRANT_COLLECTION") or "sinhala_books_v2"

c = QdrantClient(
    url=environ["QDRANT_CLUSTER_ENDPOINT"],
    api_key=environ["QDRANT_CLUSTER_API"],
    timeout=120,
)

# Guard: creating over an existing collection would drop every stored point,
# and the sparse vocab on disk would no longer match anything.
if c.collection_exists(NAME):
    raise SystemExit(
        f"collection {NAME!r} already exists — delete it explicitly if you "
        f"really mean to rebuild (this also invalidates the sparse vocab)"
    )

c.create_collection(
    collection_name=NAME,
    vectors_config={
        "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False),
            # IDF is computed server-side, so the vocab can grow as new books
            # are ingested without re-encoding existing points.
            modifier=models.Modifier.IDF,
        ),
    },
)

# scope filters
c.create_payload_index(NAME, "source_file", models.PayloadSchemaType.KEYWORD)
c.create_payload_index(NAME, "page_number", models.PayloadSchemaType.INTEGER)
c.create_payload_index(NAME, "block_type", models.PayloadSchemaType.KEYWORD)
c.create_payload_index(NAME, "user_id", models.PayloadSchemaType.KEYWORD)   # multi-tenant scoping
c.create_payload_index(NAME, "doc_id", models.PayloadSchemaType.KEYWORD)
c.create_payload_index(NAME, "lesson_title", models.PayloadSchemaType.KEYWORD)

# full-text, for topic-term matching
c.create_payload_index(
    NAME, "text",
    models.TextIndexParams(
        type="text",
        tokenizer=models.TokenizerType.WHITESPACE,
        min_token_len=2,
        lowercase=True,
    ),
)

print(f"created collection {NAME!r} with dense(1024) + sparse(IDF) and payload indexes")