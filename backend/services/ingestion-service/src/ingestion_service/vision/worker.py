from __future__ import annotations

import json
import random
import threading
import time

import structlog
from confluent_kafka import Consumer, Message, TopicPartition

from ingestion_service.config import Settings
from ingestion_service.domain import BlockType, Chunk, ChunkCreatedEvent, ImageEnrichmentRequested
from ingestion_service.messaging.producer import EventPublisher, kafka_security
from ingestion_service.observability.health import HealthRegistry
from ingestion_service.observability.metrics import VISION_CIRCUIT_OPEN, VISION_REQUESTS
from ingestion_service.pipeline.chunker import estimate_tokens
from ingestion_service.storage import ObjectStore

from .gemini import GeminiCaptioner
from .limiter import DistributedVisionGuard

log = structlog.get_logger(__name__)


class VisionRateLimited(RuntimeError):
    pass


class VisionWorker:
    def __init__(
        self,
        *,
        settings: Settings,
        store: ObjectStore,
        captioner: GeminiCaptioner,
        guard: DistributedVisionGuard,
        publisher: EventPublisher,
        health: HealthRegistry,
    ) -> None:
        self._cfg = settings
        self._store = store
        self._captioner = captioner
        self._guard = guard
        self._publisher = publisher
        self._health = health
        self._stop = threading.Event()
        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": f"{settings.kafka_group_id}-vision",
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
                "max.poll.interval.ms": 600_000,
                **kafka_security(settings),
            }
        )

    def run(self) -> None:
        self._consumer.subscribe([self._cfg.kafka_image_topic])
        self._health.consumer_running = True
        try:
            while not self._stop.is_set():
                message = self._consumer.poll(1.0)
                if message is None or message.error():
                    continue
                try:
                    self._handle(message)
                except Exception as exc:
                    log.error("vision.message_failed", error=f"{type(exc).__name__}: {exc}")
                    time.sleep(1)
                    self._consumer.seek(
                        TopicPartition(message.topic(), message.partition(), message.offset())
                    )
        finally:
            self._health.consumer_running = False
            self._consumer.close()

    def stop(self) -> None:
        self._stop.set()

    def _handle(self, message: Message) -> None:
        try:
            event = ImageEnrichmentRequested.model_validate_json(message.value())
        except Exception as exc:
            self._publisher.publish_image_dlq(
                key=message.key(),
                value=message.value(),
                reason=f"decode:{type(exc).__name__}",
            )
            self._publisher.flush_or_raise()
            self._consumer.commit(message, asynchronous=False)
            return
        caption = self._guard.cached(event.image_sha256)
        if caption is None:
            if not self._guard.reserve():
                VISION_CIRCUIT_OPEN.set(1 if self._guard.is_open() else 0)
                time.sleep(1)
                self._consumer.seek(
                    TopicPartition(message.topic(), message.partition(), message.offset())
                )
                return
            data = self._store.download_bytes(event.storage_key)
            try:
                caption = self._call_with_retry(data, event.content_type)
            except VisionRateLimited:
                time.sleep(1)
                self._consumer.seek(
                    TopicPartition(message.topic(), message.partition(), message.offset())
                )
                return
            if not caption:
                caption = event.fallback_text
            else:
                self._guard.cache(event.image_sha256, caption)
        VISION_CIRCUIT_OPEN.set(0)
        chunk = Chunk(
            text=caption,
            embed_text=caption,
            type=BlockType.IMAGE,
            section_path=event.section_path,
            page=event.page,
            chunk_index=event.chunk_index,
            token_count=estimate_tokens(caption),
            extra={
                "chunk_id": event.chunk_id,
                "doc_id": event.doc_id,
                "user_id": event.user_id,
                "source_name": event.source_name,
                "storage_key": event.storage_key,
                "image_id": event.image_sha256,
                "enrichment_pending": False,
            },
        )
        self._publisher.publish_chunk(
            ChunkCreatedEvent(
                doc_id=event.doc_id,
                user_id=event.user_id,
                source_name=event.source_name,
                require_title=bool(event.section_path),
                chunk=chunk,
            ),
            partition_key=f"{event.doc_id}:{event.page or 0}",
        )
        self._publisher.flush_or_raise()
        self._consumer.commit(message, asynchronous=False)

    def _call_with_retry(self, data: bytes, content_type: str) -> str:
        for attempt in range(1, self._cfg.vision_max_attempts + 1):
            try:
                result = self._captioner.caption(data, content_type)
                VISION_REQUESTS.labels(outcome="success").inc()
                return result
            except Exception as exc:
                message = str(exc).lower()
                rate_limited = "429" in message or "resource_exhausted" in message
                VISION_REQUESTS.labels(outcome="rate_limited" if rate_limited else "error").inc()
                if rate_limited:
                    self._guard.open(type(exc).__name__)
                    VISION_CIRCUIT_OPEN.set(1)
                    raise VisionRateLimited from exc
                if attempt >= self._cfg.vision_max_attempts:
                    log.warning("vision.fallback", error=f"{type(exc).__name__}: {exc}")
                    return ""
                time.sleep(min(30.0, (2**attempt) + random.random()))
        return ""
