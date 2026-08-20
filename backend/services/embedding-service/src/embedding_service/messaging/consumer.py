"""Kafka consumer for documents.chunks.

Delivery semantics:
- At-least-once processing
- Explicit offset commits
- Idempotent Qdrant writes
- Bounded retries
- Dead-letter queue for failed messages

The Qdrant collection is controlled only by QDRANT_COLLECTION.
A collection value received from Kafka is logged but never trusted as the
write destination.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

import structlog
from confluent_kafka import (
    Consumer,
    KafkaError,
    KafkaException,
    Message,
    Producer,
    TopicPartition,
)

from embedding_service.config.settings import KafkaSettings, Settings
from embedding_service.domain.models import IngestChunk
from embedding_service.observability.health import (
    ComponentState,
    HealthRegistry,
)
from embedding_service.observability.metrics import (
    BATCH_FAILURES,
    CONSUMER_LAG,
    DLQ_MESSAGES,
)
from embedding_service.store.ingest import IngestService


log = structlog.get_logger(__name__)

COMPONENT = "kafka-consumer"


def build_consumer_config(cfg: KafkaSettings) -> dict[str, Any]:
    conf: dict[str, Any] = {
        "bootstrap.servers": cfg.bootstrap_servers,
        "group.id": cfg.group_id,
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
        "max.poll.interval.ms": cfg.max_poll_interval_ms,
        "session.timeout.ms": cfg.session_timeout_ms,
        "security.protocol": cfg.security_protocol,
        "partition.assignment.strategy": "cooperative-sticky",
    }

    if cfg.sasl_mechanism:
        conf["sasl.mechanism"] = cfg.sasl_mechanism

    if cfg.sasl_username:
        conf["sasl.username"] = cfg.sasl_username

    if cfg.sasl_password:
        conf["sasl.password"] = cfg.sasl_password.get_secret_value()

    return conf


class DeadLetterProducer:
    """Publishes unprocessable Kafka messages to the DLQ."""

    def __init__(self, cfg: KafkaSettings) -> None:
        self._topic = cfg.dlq_topic

        producer_config: dict[str, Any] = {
            "bootstrap.servers": cfg.bootstrap_servers,
            "security.protocol": cfg.security_protocol,
        }

        if cfg.sasl_mechanism:
            producer_config["sasl.mechanism"] = cfg.sasl_mechanism

        if cfg.sasl_username:
            producer_config["sasl.username"] = cfg.sasl_username

        if cfg.sasl_password:
            producer_config["sasl.password"] = (
                cfg.sasl_password.get_secret_value()
            )

        self._producer = Producer(producer_config)

    def publish(
        self,
        *,
        key: bytes | None,
        value: bytes,
        reason: str,
    ) -> bool:
        try:
            self._producer.produce(
                self._topic,
                key=key,
                value=value,
                headers=[
                    (
                        "dlq-reason",
                        reason.encode("utf-8")[:512],
                    )
                ],
            )

            self._producer.poll(0)
            DLQ_MESSAGES.labels(reason=reason[:40]).inc()

            return True

        except (KafkaException, BufferError):
            log.error(
                "dlq.publish_failed",
                topic=self._topic,
                reason=reason,
                exc_info=True,
            )
            return False

    def flush(self, timeout: float = 5.0) -> bool:
        return self._producer.flush(timeout) == 0


class ChunkConsumer:
    """Consumes chunk events and sends them to the embedding pipeline."""

    def __init__(
        self,
        *,
        settings: Settings,
        ingest: IngestService,
        health: HealthRegistry,
        consumer: Consumer | None = None,
        dlq: DeadLetterProducer | None = None,
    ) -> None:
        self._settings = settings
        self._cfg = settings.kafka
        self._ingest = ingest
        self._health = health

        self._consumer = consumer or Consumer(
            build_consumer_config(self._cfg)
        )

        self._dlq = dlq or DeadLetterProducer(self._cfg)

        self._stopping = asyncio.Event()

        self._attempts: dict[tuple[str, int], int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Kafka partition assignment
    # ------------------------------------------------------------------

    def _on_assign(
        self,
        consumer: Consumer,
        partitions: list[TopicPartition],
    ) -> None:
        log.info(
            "kafka.assigned",
            partitions=[
                f"{partition.topic}:{partition.partition}"
                for partition in partitions
            ],
        )

        consumer.incremental_assign(partitions)

    def _on_revoke(
        self,
        consumer: Consumer,
        partitions: list[TopicPartition],
    ) -> None:
        log.info(
            "kafka.revoked",
            partitions=[
                f"{partition.topic}:{partition.partition}"
                for partition in partitions
            ],
        )

        for partition in partitions:
            self._attempts.pop(
                (partition.topic, partition.partition),
                None,
            )

        consumer.incremental_unassign(partitions)

    # ------------------------------------------------------------------
    # Message decoding
    # ------------------------------------------------------------------

    def _decode(
        self,
        messages: list[Message],
    ) -> tuple[list[IngestChunk], set[str]]:
        chunks: list[IngestChunk] = []
        event_collections: set[str] = set()

        for msg in messages:
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue

                log.error(
                    "kafka.consume_error",
                    error=str(msg.error()),
                )
                continue

            raw = msg.value()

            try:
                event = json.loads(raw)

                event_collection = event.get("collection")

                if isinstance(event_collection, str):
                    event_collection = event_collection.strip()

                    if event_collection:
                        event_collections.add(event_collection)

                payload = event.get("chunk", event)

                merged = {
                    **payload,
                    **(payload.get("extra") or {}),
                }

                chunk = IngestChunk.model_validate(merged)
                chunks.append(chunk)

            except Exception as exc:
                log.warning(
                    "kafka.undecodable",
                    partition=msg.partition(),
                    offset=msg.offset(),
                    error=str(exc)[:200],
                )

                self._dlq.publish(
                    key=msg.key(),
                    value=raw,
                    reason=f"decode:{type(exc).__name__}",
                )

        return chunks, event_collections

    # ------------------------------------------------------------------
    # Kafka offsets and lag
    # ------------------------------------------------------------------

    @staticmethod
    def _offsets_for(
        messages: list[Message],
    ) -> list[TopicPartition]:
        highest: dict[tuple[str, int], int] = {}

        for msg in messages:
            if msg.error():
                continue

            key = (msg.topic(), msg.partition())

            highest[key] = max(
                highest.get(key, -1),
                msg.offset(),
            )

        return [
            TopicPartition(topic, partition, offset + 1)
            for (topic, partition), offset in highest.items()
        ]

    def _record_lag(
        self,
        messages: list[Message],
    ) -> None:
        try:
            checked_partitions: set[tuple[str, int]] = set()

            for msg in messages:
                if msg.error():
                    continue

                key = (msg.topic(), msg.partition())

                if key in checked_partitions:
                    continue

                checked_partitions.add(key)

                _, high = self._consumer.get_watermark_offsets(
                    TopicPartition(
                        msg.topic(),
                        msg.partition(),
                    ),
                    timeout=1.0,
                    cached=True,
                )

                CONSUMER_LAG.labels(
                    partition=str(msg.partition())
                ).set(
                    max(
                        0,
                        high - msg.offset() - 1,
                    )
                )

        except KafkaException:
            log.debug(
                "kafka.lag_unavailable",
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Dead-letter handling
    # ------------------------------------------------------------------

    def _dead_letter_batch(
        self,
        messages: list[Message],
        reason: str,
    ) -> bool:
        accepted = True

        for msg in messages:
            if msg.error():
                continue

            published = self._dlq.publish(
                key=msg.key(),
                value=msg.value(),
                reason=reason,
            )

            accepted = published and accepted

        return accepted and self._dlq.flush()

    # ------------------------------------------------------------------
    # Main consumer loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        cfg = self._cfg
        loop = asyncio.get_running_loop()

        self._consumer.subscribe(
            [cfg.chunks_topic],
            on_assign=self._on_assign,
            on_revoke=self._on_revoke,
        )

        configured_collection = self._settings.qdrant.collection

        self._health.set(
            COMPONENT,
            ComponentState.HEALTHY,
            (
                f"topic={cfg.chunks_topic},"
                f"collection={configured_collection}"
            ),
        )

        log.info(
            "kafka.started",
            topic=cfg.chunks_topic,
            batch_size=cfg.batch_size,
            qdrant_collection=configured_collection,
        )

        try:
            while not self._stopping.is_set():
                messages = await loop.run_in_executor(
                    None,
                    lambda: self._consumer.consume(
                        num_messages=cfg.batch_size,
                        timeout=cfg.batch_timeout_seconds,
                    ),
                )

                if not messages:
                    continue

                self._record_lag(messages)

                await self._process(messages)

        except asyncio.CancelledError:
            log.info("kafka.cancelled")
            raise

        except Exception as exc:
            self._health.set(
                COMPONENT,
                ComponentState.FAILED,
                str(exc)[:200],
            )

            log.error(
                "kafka.loop_failed",
                exc_info=True,
            )
            raise

        finally:
            self._health.set(
                COMPONENT,
                ComponentState.STOPPED,
            )

            self._dlq.flush()
            self._consumer.close()

            log.info("kafka.stopped")

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    async def _process(
        self,
        messages: list[Message],
    ) -> None:
        first_offsets: dict[tuple[str, int], int] = {}

        for message in messages:
            if message.error():
                continue

            key = (
                message.topic(),
                message.partition(),
            )

            first_offsets[key] = min(
                first_offsets.get(
                    key,
                    message.offset(),
                ),
                message.offset(),
            )

        chunks, event_collections = self._decode(messages)

        if not chunks:
            self._dlq.flush()

            self._consumer.commit(
                offsets=self._offsets_for(messages),
                asynchronous=False,
            )
            return

        # The configured collection is always authoritative.
        target = self._settings.qdrant.collection

        mismatched_collections = sorted(
            collection
            for collection in event_collections
            if collection != target
        )

        if mismatched_collections:
            log.warning(
                "kafka.event_collection_ignored",
                event_collections=mismatched_collections,
                configured_collection=target,
            )

        try:
            await self._ingest.ingest_batch(
                chunks,
                collection=target,
            )

        except Exception as exc:
            for partition_key in first_offsets:
                self._attempts[partition_key] += 1

            attempts = max(
                (
                    self._attempts[key]
                    for key in first_offsets
                ),
                default=1,
            )

            BATCH_FAILURES.labels(stage="ingest").inc()

            if attempts >= self._cfg.max_batch_attempts:
                log.error(
                    "kafka.batch_dead_lettered",
                    attempts=attempts,
                    size=len(messages),
                    configured_collection=target,
                    error=str(exc)[:200],
                )

                delivered = self._dead_letter_batch(
                    messages,
                    reason=f"ingest:{type(exc).__name__}",
                )

                if delivered:
                    self._consumer.commit(
                        offsets=self._offsets_for(messages),
                        asynchronous=False,
                    )

                    for partition_key in first_offsets:
                        self._attempts.pop(
                            partition_key,
                            None,
                        )
                else:
                    for (
                        topic,
                        partition,
                    ), offset in first_offsets.items():
                        self._consumer.seek(
                            TopicPartition(
                                topic,
                                partition,
                                offset,
                            )
                        )

            else:
                log.warning(
                    "kafka.batch_failed_will_retry",
                    attempt=attempts,
                    max_attempts=self._cfg.max_batch_attempts,
                    configured_collection=target,
                    error=str(exc)[:200],
                )

                for (
                    topic,
                    partition,
                ), offset in first_offsets.items():
                    self._consumer.seek(
                        TopicPartition(
                            topic,
                            partition,
                            offset,
                        )
                    )

                await asyncio.sleep(
                    min(2**attempts, 30)
                )

            return

        for partition_key in first_offsets:
            self._attempts.pop(
                partition_key,
                None,
            )

        self._consumer.commit(
            offsets=self._offsets_for(messages),
            asynchronous=False,
        )

        log.info(
            "kafka.batch_ingested",
            chunks=len(chunks),
            collection=target,
        )

    async def stop(self) -> None:
        self._stopping.set()