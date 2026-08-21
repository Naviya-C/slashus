from __future__ import annotations

import tempfile
from pathlib import Path

import structlog

from ingestion_service.config import Settings
from ingestion_service.documents import ReaderRegistry
from ingestion_service.domain import (
    BlockType,
    Chunk,
    ChunkCreatedEvent,
    DocumentIngestedEvent,
    DocumentUploadedEvent,
    ImageEnrichmentRequested,
    stable_chunk_id,
)
from ingestion_service.messaging.producer import EventPublisher
from ingestion_service.observability.metrics import (
    CHUNKS_PUBLISHED,
    DOCUMENTS_COMPLETED,
    DOCUMENTS_FAILED,
    DOCUMENT_SECONDS,
    IMAGES_QUEUED,
    UNITS_PROCESSED,
)
from ingestion_service.storage import ObjectStore, asset_key

from .chunker import BlockChunker, estimate_tokens
from .jobs import JobRepository

log = structlog.get_logger(__name__)


class IngestionService:
    def __init__(
        self,
        *,
        settings: Settings,
        source_store: ObjectStore,
        asset_store: ObjectStore,
        readers: ReaderRegistry,
        publisher: EventPublisher,
        jobs: JobRepository,
    ) -> None:
        self._cfg = settings
        self._source = source_store
        self._assets = asset_store
        self._readers = readers
        self._publisher = publisher
        self._jobs = jobs
        self._chunker = BlockChunker(
            max_tokens=settings.chunk_max_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )

    def ingest(self, event: DocumentUploadedEvent) -> DocumentIngestedEvent:
        job_id = event.effective_job_id
        self._jobs.begin_attempt(event)
        units_processed = 0
        chunks_published = 0
        images_queued = 0
        suffix = Path(event.source_name).suffix or _suffix_for(event.content_type)
        try:
            with DOCUMENT_SECONDS.time(), tempfile.TemporaryDirectory(prefix="ingestion-") as tmp:
                source_path = Path(tmp) / f"source{suffix}"
                size = self._source.download_to_file(event.storage_key, source_path)
                if size > self._cfg.max_document_bytes:
                    raise ValueError(f"document is {size} bytes; configured limit exceeded")
                for unit in self._readers.units(source_path, event.content_type):
                    units_processed += 1
                    if units_processed > self._cfg.max_document_units:
                        raise ValueError("document unit limit exceeded")
                    chunks = self._chunker.chunks(
                        unit.blocks,
                        page=unit.number,
                        start_index=chunks_published,
                    )
                    for asset in unit.assets:
                        image_chunk, request = self._image_events(
                            event=event,
                            asset=asset,
                            unit_number=unit.number,
                            chunk_index=chunks_published + len(chunks),
                            section_path=_section_for_unit(unit),
                        )
                        chunks.append(image_chunk)
                        if request is not None:
                            self._publisher.publish_image(request)
                            images_queued += 1
                            IMAGES_QUEUED.inc()
                    for chunk in chunks:
                        self._stamp_chunk(chunk, event, unit.number)
                        self._publisher.publish_chunk(
                            ChunkCreatedEvent(
                                doc_id=event.doc_id,
                                user_id=event.user_id,
                                source_name=event.source_name,
                                require_title=bool(chunk.section_path),
                                chunk=chunk,
                            ),
                            partition_key=f"{event.doc_id}:{unit.number}",
                        )
                        chunks_published += 1
                        CHUNKS_PUBLISHED.inc()
                    self._publisher.poll()
                    UNITS_PROCESSED.inc()
                    self._jobs.progress(
                        job_id,
                        units_processed=units_processed,
                        chunks_published=chunks_published,
                        images_queued=images_queued,
                    )
                self._publisher.flush_or_raise()
            completed = DocumentIngestedEvent(
                doc_id=event.doc_id,
                user_id=event.user_id,
                job_id=job_id,
                source_name=event.source_name,
                units_processed=units_processed,
                chunks_published=chunks_published,
                images_queued=images_queued,
            )
            self._publisher.publish_completed(completed)
            self._publisher.flush_or_raise()
            self._jobs.complete(job_id)
            DOCUMENTS_COMPLETED.inc()
            log.info(
                "document.completed",
                doc_id=event.doc_id,
                units=units_processed,
                chunks=chunks_published,
                images=images_queued,
            )
            return completed
        except Exception as exc:
            DOCUMENTS_FAILED.labels(reason=type(exc).__name__).inc()
            self._jobs.fail(job_id, f"{type(exc).__name__}: {exc}")
            raise

    def _image_events(
        self,
        *,
        event: DocumentUploadedEvent,
        asset,
        unit_number: int,
        chunk_index: int,
        section_path: list[str],
    ) -> tuple[Chunk, ImageEnrichmentRequested | None]:
        key = asset_key(event.user_id, event.doc_id, asset.digest, asset.extension)
        self._assets.upload_bytes(key, asset.data, content_type=asset.content_type)
        fallback = asset.ocr_text.strip() or (
            f"Image from {event.source_name}, unit {unit_number}, "
            f"dimensions {asset.width}x{asset.height}."
        )
        chunk_id = stable_chunk_id(event.doc_id, unit_number, BlockType.IMAGE, chunk_index)
        chunk = Chunk(
            text=fallback,
            embed_text=fallback,
            type=BlockType.IMAGE,
            section_path=section_path,
            page=unit_number,
            bbox=asset.bbox,
            chunk_index=chunk_index,
            token_count=estimate_tokens(fallback),
            extra={
                "chunk_id": chunk_id,
                "image_id": asset.digest,
                "storage_key": key,
                "width": asset.width,
                "height": asset.height,
                "ocr": bool(asset.ocr_text),
                "enrichment_pending": self._cfg.vision_enrichment_enabled,
            },
        )
        request = None
        if self._cfg.vision_enrichment_enabled:
            request = ImageEnrichmentRequested(
                doc_id=event.doc_id,
                user_id=event.user_id,
                source_name=event.source_name,
                chunk_id=chunk_id,
                chunk_index=chunk_index,
                page=unit_number,
                section_path=section_path,
                storage_key=key,
                content_type=asset.content_type,
                image_sha256=asset.digest,
                fallback_text=fallback,
            )
        return chunk, request

    @staticmethod
    def _stamp_chunk(chunk: Chunk, event: DocumentUploadedEvent, unit_number: int) -> None:
        chunk.extra.setdefault(
            "chunk_id",
            stable_chunk_id(event.doc_id, unit_number, chunk.type, chunk.chunk_index),
        )
        chunk.extra.update(
            {
                "doc_id": event.doc_id,
                "user_id": event.user_id,
                "source_name": event.source_name,
            }
        )


def _section_for_unit(unit) -> list[str]:
    for block in unit.blocks:
        if block.section_path:
            return list(block.section_path)
    return [unit.label] if unit.label else []


def _suffix_for(content_type: str) -> str:
    return {
        "application/pdf": ".pdf",
        "application/json": ".json",
        "text/plain": ".txt",
        "text/html": ".html",
        "image/png": ".png",
        "image/jpeg": ".jpg",
    }.get(content_type, ".bin")
