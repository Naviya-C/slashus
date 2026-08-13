"""Ingestion use-case: filter, embed, upsert."""

from __future__ import annotations

import re
from typing import Any

import structlog

from embedding_service.config.settings import Settings
from embedding_service.domain.models import BlockType, ChunkPayload, IngestChunk
from embedding_service.observability.metrics import (
    CHUNKS_INGESTED,
    CHUNKS_SKIPPED,
    INGEST_DURATION,
)

log = structlog.get_logger(__name__)

_LESSON_RE = re.compile(r"^\s*(\d+)\s+(.*)$")

# Length filtering is skipped for these: a table or an image caption is short
# by nature, and dropping them loses content the text filter was never aimed at.
_LENGTH_EXEMPT = frozenset({BlockType.TABLE, BlockType.IMAGE})

# Payload keys carried through from the ingest event when present. Named
# explicitly rather than copying ``extra`` wholesale, so an upstream service
# adding a field cannot silently widen this service's storage contract.
_CARRIED_KEYS = (
    "table_id",
    "n_rows",
    "n_cols",
    "image_id",
    "storage_key",
    "storage_url",
    "width",
    "height",
)


def word_count(text: str) -> int:
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


def should_embed(chunk: IngestChunk, *, min_words: int) -> tuple[bool, str]:
    """Quality gate. Returns (keep, reason).

    Short chunks are layout debris -- page numbers, running headers, printer
    marks. Each costs a forward pass, a point, and an index slot, and they
    actively dilute retrieval.
    """
    text = (chunk.embed_text or "").strip()
    if not text:
        return False, "empty"
    if chunk.block_type in _LENGTH_EXEMPT:
        return True, ""
    if word_count(text) < min_words:
        return False, "too_short"
    return True, ""


def to_payload(chunk: IngestChunk) -> ChunkPayload:
    """Map an ingest chunk onto the stored payload contract."""
    raw_title = chunk.section_path[0] if chunk.section_path else None
    lesson_number: int | None = None
    lesson_title = raw_title

    if raw_title and (m := _LESSON_RE.match(raw_title)):
        lesson_number = int(m.group(1))
        lesson_title = m.group(2).strip()

    extras = {k: chunk.extra[k] for k in _CARRIED_KEYS if k in chunk.extra}

    return ChunkPayload(
        text=chunk.text,
        chunk_id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        user_id=chunk.user_id,
        lesson_title=lesson_title,
        lesson_number=lesson_number,
        page_number=chunk.page,
        block_type=chunk.block_type.value,
        chunk_index=chunk.chunk_index,
        token_count=chunk.token_count,
        source_file=chunk.source_name,
        **extras,
    )


class IngestService:
    def __init__(
        self,
        *,
        settings: Settings,
        store: Any,
        dense: Any,
        sparse: Any,
        redis: Any = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._dense = dense
        self._sparse = sparse
        self._redis = redis

    async def ingest_batch(self, chunks: list[IngestChunk], *, collection: str) -> int:
        """Embed and upsert a batch. Returns how many points were written.

        Writes are idempotent: the point id is uuid5 of the chunk id, so a
        Kafka redelivery overwrites its own point instead of duplicating it.
        That is what makes at-least-once delivery safe here.
        """
        if not chunks:
            return 0

        min_words = self._settings.retrieval.min_chunk_words
        keep: list[IngestChunk] = []
        for chunk in chunks:
            ok, reason = should_embed(chunk, min_words=min_words)
            if ok:
                keep.append(chunk)
            else:
                CHUNKS_SKIPPED.labels(reason=reason).inc()
                log.debug("ingest.skipped", chunk_id=chunk.chunk_id, reason=reason)

        if not keep:
            return 0

        with INGEST_DURATION.time():
            texts = [c.embed_text for c in keep]
            dense_vectors = await self._dense.embed_documents(texts)
            sparse_vectors = self._sparse.encode_batch(texts)

            points = [
                (chunk.point_id, dense_vec, sparse_vec, to_payload(chunk))
                for chunk, dense_vec, sparse_vec in zip(
                    keep, dense_vectors, sparse_vectors, strict=True
                )
            ]
            written = await self._store.upsert(collection=collection, points=points)

        if self._redis is not None and written:
            try:
                async with self._redis.pipeline(transaction=False) as pipe:
                    for user_id in sorted({chunk.user_id for chunk in keep}):
                        pipe.incr(f"semcache:docgen:{user_id}")
                    await pipe.execute()
            except Exception:
                log.warning("ingest.cache_invalidation_failed", exc_info=True)

        CHUNKS_INGESTED.inc(written)
        log.info(
            "ingest.batch_stored",
            collection=collection,
            written=written,
            received=len(chunks),
            skipped=len(chunks) - len(keep),
        )
        return written
