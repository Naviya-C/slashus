from __future__ import annotations

import threading
import time

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException, Message, TopicPartition

from ingestion_service.config import Settings
from ingestion_service.domain import DocumentUploadedEvent
from ingestion_service.observability.health import HealthRegistry
from ingestion_service.observability.metrics import CONSUMER_LAG, DLQ_DOCUMENTS
from ingestion_service.pipeline import IngestionService, JobRepository

from .producer import EventPublisher, kafka_security

log = structlog.get_logger(__name__)


class DocumentConsumer:
    def __init__(
        self,
        *,
        settings: Settings,
        service: IngestionService,
        jobs: JobRepository,
        publisher: EventPublisher,
        health: HealthRegistry,
        consumer: Consumer | None = None,
    ) -> None:
        self._cfg = settings
        self._service = service
        self._jobs = jobs
        self._publisher = publisher
        self._health = health
        self._consumer = consumer or Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": settings.kafka_group_id,
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
                "auto.offset.reset": "earliest",
                "max.poll.interval.ms": settings.kafka_max_poll_interval_ms,
                "session.timeout.ms": 45_000,
                "partition.assignment.strategy": "cooperative-sticky",
                **kafka_security(settings),
            }
        )
        self._stop = threading.Event()

    def run(self) -> None:
        self._consumer.subscribe([self._cfg.kafka_upload_topic])
        self._health.consumer_running = True
        log.info("consumer.started", topic=self._cfg.kafka_upload_topic)
        try:
            while not self._stop.is_set():
                message = self._consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    if message.error().code() != KafkaError._PARTITION_EOF:
                        log.error("consumer.error", error=str(message.error()))
                    continue
                self._record_lag(message)
                self._handle(message)
        finally:
            self._health.consumer_running = False
            self._consumer.close()
            log.info("consumer.stopped")

    def stop(self) -> None:
        self._stop.set()

    def _handle(self, message: Message) -> None:
        raw = message.value()
        try:
            event = DocumentUploadedEvent.model_validate_json(raw)
        except Exception as exc:
            self._dead_letter_and_commit(message, f"decode:{type(exc).__name__}")
            return
        state = self._jobs.get(event.effective_job_id)
        if state and state.status.value == "completed":
            self._commit(message)
            return
        if state and state.attempts >= self._cfg.kafka_max_document_attempts:
            self._dead_letter_and_commit(message, "ingest:attempts_exhausted")
            return
        try:
            self._service.ingest(event)
        except Exception as exc:
            state = self._jobs.get(event.effective_job_id)
            attempts = state.attempts if state else 1
            log.error(
                "document.failed",
                doc_id=event.doc_id,
                attempts=attempts,
                error=f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )
            if attempts >= self._cfg.kafka_max_document_attempts:
                self._dead_letter_and_commit(message, f"ingest:{type(exc).__name__}")
            else:
                time.sleep(min(30.0, float(2**attempts)))
                self._consumer.seek(
                    TopicPartition(message.topic(), message.partition(), message.offset())
                )
            return
        self._commit(message)

    def _dead_letter_and_commit(self, message: Message, reason: str) -> None:
        self._publisher.publish_dlq(key=message.key(), value=message.value(), reason=reason)
        self._publisher.flush_or_raise()
        DLQ_DOCUMENTS.labels(reason=reason[:40]).inc()
        self._commit(message)

    def _commit(self, message: Message) -> None:
        offsets = [TopicPartition(message.topic(), message.partition(), message.offset() + 1)]
        self._consumer.commit(offsets=offsets, asynchronous=False)

    def _record_lag(self, message: Message) -> None:
        try:
            _, high = self._consumer.get_watermark_offsets(
                TopicPartition(message.topic(), message.partition()),
                cached=True,
            )
            CONSUMER_LAG.labels(partition=str(message.partition())).set(
                max(0, high - message.offset() - 1)
            )
        except KafkaException:
            log.debug("consumer.lag_unavailable")
