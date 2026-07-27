from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client import models

from embedding_service.embedding.payload import point_id, to_payload

log = logging.getLogger(__name__)


@dataclass(slots=True)
class EmbedDeps:
    dense: object
    sparse: object
    client: object


def embed_and_store_chunk(
    *,
    chunk,
    collection: str,
    deps: EmbedDeps,
) -> bool:
    """
    Embed and store a single chunk.

    Returns True if stored.
    Returns False if skipped because embed_text is empty.
    """

    if not chunk.embed_text or not chunk.embed_text.strip():
        log.warning(
            "skipping chunk %s: empty embed_text",
            chunk.extra["chunk_id"],
        )
        return False

    text = chunk.embed_text

    dense_vector = deps.dense.embed_documents([text])[0]

    sparse_indices, sparse_values = (
        deps.sparse.encode_documents([text])[0]
    )

    point = models.PointStruct(
        id=point_id(chunk.extra["chunk_id"]),
        vector={
            "dense": dense_vector,
            "sparse": models.SparseVector(
                indices=sparse_indices,
                values=sparse_values,
            ),
        },
        payload=to_payload(chunk),
    )

    deps.client.upsert(
        collection_name=collection,
        points=[point],
        wait=True,
    )

    if hasattr(deps.sparse, "save"):
        deps.sparse.save()

    log.info(
        "stored chunk %s",
        chunk.extra["chunk_id"],
    )

    return True