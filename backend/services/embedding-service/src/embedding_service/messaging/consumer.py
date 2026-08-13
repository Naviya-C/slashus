"""Kafka consumer for ``documents.chunks``.

WHAT CHANGED
------------
* DEAD-LETTER QUEUE. Previously an undecodable message was logged and dropped
  (silent data loss), and a batch that always failed was redelivered forever --
  the partition stalled permanently while the topic looked healthy and ingest
  quietly stopped. A batch now gets a bounded number of attempts; after that
  the offending messages go to a DLQ topic and the consumer moves on.

* EXPLICIT OFFSET COMMITS. ``commit(asynchronous=False)`` with no arguments
  commits the consumer's current position on every assigned partition, which
  is only accidentally correct. Offsets are now derived from the messages
  actually processed.

* REBALANCE HANDLING. Without ``on_revoke`` an in-flight batch could have its
  partitions reassigned mid-work and the subsequent commit would raise. The
  handler now stops the batch cleanly and lets the new owner redeliver -- safe
  because writes are idempotent.

* LAG METRICS. Consumer lag is the health signal for an ingest pipeline and
  was not measured anywhere.

DELIVERY SEMANTICS
------------------
At-least-once with idempotent writes. Offsets commit only after the whole batch
lands, so a crash mid-batch redelivers up to ``batch_size`` chunks. That is safe
because the point id is uuid5 of the chunk id: a replay overwrites its own point.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException, Message, Producer, TopicPartition

from embedding_service.config.settings import KafkaSettings, Settings
from embedding_service.domain.models import IngestChunk
from embedding_service.observability.health import ComponentState, HealthRegistry
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
        # Cooperative rebalancing: an added replica takes over a subset of
        # partitions instead of every consumer dropping everything and
        # re-acquiring, which with a slow CPU embedder means a long stall.
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
    """Publishes unprocessable messages with the failure reason attached."""

    def __init__(self, cfg: KafkaSettings) -> None:
        self._topic = cfg.dlq_topic
        self._producer = Producer(
            {"bootstrap.servers": cfg.bootstrap_servers, "security.protocol": cfg.security_protocol}
        )

    def publish(self, *, key: bytes | None, value: bytes, reason: str) -> bool:
        try:
            self._producer.produce(
                self._topic,
                key=key,
                value=value,
                headers=[("dlq-reason", reason.encode("utf-8")[:512])],
            )
            self._producer.poll(0)
            DLQ_MESSAGES.labels(reason=reason[:40]).inc()
            return True
        except (KafkaException, BufferError):
            # If the DLQ itself is unavailable, log loudly and drop. Blocking
            # the consumer on a broken DLQ turns one bad message into a total
            # ingest outage.
            log.error("dlq.publish_failed", topic=self._topic, reason=reason, exc_info=True)
            return False

    def flush(self, timeout: float = 5.0) -> bool:
        return self._producer.flush(timeout) == 0


class ChunkConsumer:
    """Polls Kafka on a worker thread and drives ingestion on the event loop."""

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
        self._consumer = consumer or Consumer(build_consumer_config(self._cfg))
        self._dlq = dlq or DeadLetterProducer(self._cfg)
        self._stopping = asyncio.Event()
        self._attempts: dict[tuple[str, int], int] = defaultdict(int)

    # -- rebalance --------------------------------------------------------

    def _on_assign(self, consumer: Consumer, partitions: list[TopicPartition]) -> None:
        log.info("kafka.assigned", partitions=[f"{p.topic}:{p.partition}" for p in partitions])
        consumer.incremental_assign(partitions)

    def _on_revoke(self, consumer: Consumer, partitions: list[TopicPartition]) -> None:
        log.info("kafka.revoked", partitions=[f"{p.topic}:{p.partition}" for p in partitions])
        for p in partitions:
            self._attempts.pop((p.topic, p.partition), None)
        consumer.incremental_unassign(partitions)

    # -- decoding ---------------------------------------------------------

    def _decode(self, messages: list[Message]) -> tuple[list[IngestChunk], str | None]:
        """Decode messages, dead-lettering any that cannot be parsed.

        Returns the chunks and the collection they belong to. Previously a
        malformed message was logged and dropped; it now lands in the DLQ so it
        is recoverable and countable.
        """
        chunks: list[IngestChunk] = []
        collection: str | None = None

        for msg in messages:
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                log.error("kafka.consume_error", error=str(msg.error()))
                continue

            raw = msg.value()
            try:
                event = json.loads(raw)
                collection = event.get("collection") or collection
                payload = event.get("chunk", event)
                # Ingest events nest identifiers under `extra`; flatten so the
                # model validates them as first-class required fields rather
                # than the caller reaching into a dict and raising KeyError.
                merged = {**payload, **(payload.get("extra") or {})}
                chunks.append(IngestChunk.model_validate(merged))
            except Exception as exc:
                log.warning(
                    "kafka.undecodable",
                    partition=msg.partition(),
                    offset=msg.offset(),
                    error=str(exc)[:200],
                )
                self._dlq.publish(key=msg.key(), value=raw, reason=f"decode:{type(exc).__name__}")

        return chunks, collection

    # -- offsets ----------------------------------------------------------

    @staticmethod
    def _offsets_for(messages: list[Message]) -> list[TopicPartition]:
        """Highest offset seen per partition, plus one -- the resume point."""
        highest: dict[tuple[str, int], int] = {}
        for msg in messages:
            if msg.error():
                continue
            key = (msg.topic(), msg.partition())
            highest[key] = max(highest.get(key, -1), msg.offset())
        return [TopicPartition(topic, part, off + 1) for (topic, part), off in highest.items()]

    def _record_lag(self, messages: list[Message]) -> None:
        try:
            for msg in messages:
                if msg.error():
                    continue
                _, high = self._consumer.get_watermark_offsets(
                    TopicPartition(msg.topic(), msg.partition()), timeout=1.0, cached=True
                )
                CONSUMER_LAG.labels(partition=str(msg.partition())).set(
                    max(0, high - msg.offset() - 1)
                )
        except KafkaException:
            log.debug("kafka.lag_unavailable", exc_info=True)

    def _dead_letter_batch(self, messages: list[Message], reason: str) -> bool:
        accepted = True
        for msg in messages:
            if not msg.error():
                accepted = (
                    self._dlq.publish(key=msg.key(), value=msg.value(), reason=reason) and accepted
                )
        return accepted and self._dlq.flush()

    # -- main loop --------------------------------------------------------

    async def run(self) -> None:
        cfg = self._cfg
        loop = asyncio.get_running_loop()

        self._consumer.subscribe(
            [cfg.chunks_topic], on_assign=self._on_assign, on_revoke=self._on_revoke
        )
        self._health.set(COMPONENT, ComponentState.HEALTHY, f"topic={cfg.chunks_topic}")
        log.info("kafka.started", topic=cfg.chunks_topic, batch_size=cfg.batch_size)

        try:
            while not self._stopping.is_set():
                # consume() blocks; run it off the event loop so the gRPC and
                # HTTP servers in this process stay responsive.
                messages = await loop.run_in_executor(
                    None,
                    lambda: self._consumer.consume(
                        num_messages=cfg.batch_size, timeout=cfg.batch_timeout_seconds
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
            # Reported as FAILED rather than killed with os._exit: readiness
            # goes red, the orchestrator stops routing to this instance, and
            # shutdown still runs its cleanup.
            self._health.set(COMPONENT, ComponentState.FAILED, str(exc)[:200])
            log.error("kafka.loop_failed", exc_info=True)
            raise
        finally:
            self._health.set(COMPONENT, ComponentState.STOPPED)
            self._dlq.flush()
            self._consumer.close()
            log.info("kafka.stopped")

    async def _process(self, messages: list[Message]) -> None:
        first_offsets: dict[tuple[str, int], int] = {}
        for message in messages:
            if message.error():
                continue
            key = (message.topic(), message.partition())
            first_offsets[key] = min(first_offsets.get(key, message.offset()), message.offset())
        chunks, collection = self._decode(messages)

        if not chunks:
            self._consumer.commit(offsets=self._offsets_for(messages), asynchronous=False)
            return

        target = collection or self._settings.qdrant.collection

        try:
            await self._ingest.ingest_batch(chunks, collection=target)
        except Exception as exc:
            for partition_key in first_offsets:
                self._attempts[partition_key] += 1
            attempts = max((self._attempts[key] for key in first_offsets), default=1)
            BATCH_FAILURES.labels(stage="ingest").inc()

            if attempts >= self._cfg.max_batch_attempts:
                # Bounded: the batch has failed repeatedly, so it is treated as
                # poison and moved aside. Without this the partition never
                # advances and every later document waits behind it forever.
                log.error(
                    "kafka.batch_dead_lettered",
                    attempts=attempts,
                    size=len(messages),
                    error=str(exc)[:200],
                )
                delivered = self._dead_letter_batch(messages, reason=f"ingest:{type(exc).__name__}")
                if delivered:
                    self._consumer.commit(offsets=self._offsets_for(messages), asynchronous=False)
                    for partition_key in first_offsets:
                        self._attempts.pop(partition_key, None)
                else:
                    for (topic, partition), offset in first_offsets.items():
                        self._consumer.seek(TopicPartition(topic, partition, offset))
            else:
                log.warning(
                    "kafka.batch_failed_will_retry",
                    attempt=attempts,
                    max_attempts=self._cfg.max_batch_attempts,
                    error=str(exc)[:200],
                )
                for (topic, partition), offset in first_offsets.items():
                    self._consumer.seek(TopicPartition(topic, partition, offset))
                await asyncio.sleep(min(2**attempts, 30))
            return

        for partition_key in first_offsets:
            self._attempts.pop(partition_key, None)
        self._consumer.commit(offsets=self._offsets_for(messages), asynchronous=False)

    async def stop(self) -> None:
        self._stopping.set()
