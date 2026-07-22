from __future__ import annotations
import logging
from dataclasses import dataclass
from qdrant_client import models
from src.ingestion.embedding.payload import to_payload, point_id
from src.ingestion.embedding.cleaning import drop_untitled

log = logging.getLogger(__name__)


@dataclass
class EmbedDeps:
    dense: object      # DenseEmbedder
    sparse: object     # SparseEncoder
    client: object     # QdrantClient


def embed_and_store(chunks, *, collection: str, deps: EmbedDeps, batch: int = 48,
                    require_title: bool = True) -> int:
    """Embed + upsert. `require_title=False` for fully-scanned documents,
    where OCR chunks legitimately have no heading (see cleaning.py)."""
    usable = [c for c in chunks if c.embed_text and c.embed_text.strip()]
    if len(usable) != len(chunks):
        log.warning("skipped %d chunks with empty embed_text", len(chunks) - len(usable))

    if require_title:
        usable = drop_untitled(usable)

    stored = 0
    for i in range(0, len(usable), batch):
        window = usable[i:i + batch]
        texts = [c.embed_text for c in window]          # NOT c.text

        dense_vecs = deps.dense.embed_documents(texts)
        sparse_vecs = deps.sparse.encode_documents(texts)

        points = [
            models.PointStruct(
                id=point_id(c.extra["chunk_id"]),
                vector={"dense": dv, "sparse": models.SparseVector(indices=idx, values=vals)},
                payload=to_payload(c),
            )
            for c, dv, (idx, vals) in zip(window, dense_vecs, sparse_vecs)
        ]
        deps.client.upsert(collection_name=collection, points=points, wait=True)
        stored += len(points)
        log.info("stored %d/%d", stored, len(usable))

    # the sparse vocab is a build artifact the agent service must load
    # identically — persist it after every store so it's never stale
    if hasattr(deps.sparse, "save"):
        deps.sparse.save()
    return stored