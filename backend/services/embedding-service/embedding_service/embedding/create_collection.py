"""
One-time setup for a collection: vectors config + payload indexes.

Run as a module from the repo root so imports resolve the same way they do
everywhere else in the package:

    python -m embedding_service.embedding.create_collection

Re-running is safe: an existing collection is left alone rather than
overwritten, so this cannot silently destroy an indexed corpus.
"""

from __future__ import annotations
from qdrant_client import QdrantClient, models

from embedding_service.config import load_env

environ = load_env()

NAME = environ.get("QDRANT_COLLECTION") or "sinhala_books_v3"

c = QdrantClient(
    url=environ["QDRANT_CLUSTER_ENDPOINT"],
    api_key=environ["QDRANT_CLUSTER_API"],
    timeout=120,
)

if c.collection_exists(NAME):
    raise SystemExit(
        f"collection {NAME!r} already exists — delete it explicitly if you \
        really mean to rebuild (this also invalidates the sparse vocab)"
    )

c.create_collection(
    collection_name=NAME,
    vectors_config={
        "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False), # Keep on_disk as false cause keep those in RAM for fast retrieval
            modifier=models.Modifier.IDF, # Give rare terms to more import and less for common terms
        ),
    },
)

# Adding index in to payload, then it gives fast filtering
c.create_payload_index(NAME, "source_file", models.PayloadSchemaType.KEYWORD)
c.create_payload_index(NAME, "page_number", models.PayloadSchemaType.INTEGER)
c.create_payload_index(NAME, "block_type", models.PayloadSchemaType.KEYWORD)
c.create_payload_index(NAME, "user_id", models.PayloadSchemaType.KEYWORD)   # multi-tenant scoping
c.create_payload_index(NAME, "doc_id", models.PayloadSchemaType.KEYWORD)
c.create_payload_index(NAME, "lesson_title", models.PayloadSchemaType.KEYWORD)

c.create_payload_index(
    NAME, "text",
    models.TextIndexParams( 
        type="text",
        tokenizer=models.TokenizerType.WHITESPACE,
        min_token_len=2, # Ignore tokens less than 2 
        lowercase=True,
    ),
)


print(f"created collection {NAME!r} with dense(1024) + sparse(IDF) and payload indexes")