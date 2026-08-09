# embedding_service/embedding/store.py
from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client import models

from embedding_service.embedding.cleaning import should_embed
from embedding_service.embedding.payload import point_id, to_payload

log = logging.getLogger(__name__)


@dataclass(slots=True)
class EmbedDeps:
    dense: object
    sparse: object
    client: object


def embed_and_store_chunks(
    *,
    chunks,
    collection: str,
    deps: EmbedDeps,
) -> int:
    """
    Embed and upsert a BATCH of chunks. Returns how many were stored.
    """
    keep = [c for c in chunks if should_embed(c)]

    if not keep:
        return 0

    texts = [c.embed_text for c in keep]

    dense = deps.dense.embed_documents(texts)
    sparse = deps.sparse.encode_documents(texts)

    points = [
        models.PointStruct(
            id=point_id(c.extra["chunk_id"]),
            vector={
                "dense": vec,
                "sparse": models.SparseVector(indices=idx, values=val),
            },
            payload=to_payload(c),
        )
        for c, vec, (idx, val) in zip(keep, dense, sparse)
    ]

    deps.client.upsert(collection_name=collection, points=points, wait=True)

    if hasattr(deps.sparse, "save"):
        deps.sparse.save()

    log.info("stored %d/%d chunks in %s", len(points), len(chunks), collection)
    return len(points)


def embed_and_store_chunk(
    *,
    chunk,
    collection: str,
    deps: EmbedDeps,
) -> bool:
    return (
        embed_and_store_chunks(
            chunks=[chunk],
            collection=collection,
            deps=deps,
        )
        == 1
    )