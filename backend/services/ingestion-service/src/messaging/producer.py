"""
messaging/producer.py
=====================

Publishes ONE ChunkCreatedEvent per Kafka message.

Each call to publish() sends exactly one chunk to the embedding
service. This keeps Kafka messages small and enables parallel
embedding, retries, and idempotent processing.
"""

from __future__ import annotations

import json
import logging
import os

from confluent_kafka import Producer

from contracts import ChunkCreatedEvent

log = logging.getLogger(__name__)


class ChunkPublisher:
    def __init__(
        self,
        *,
        bootstrap: str,
        topic: str,
    ):
        self._topic = topic

        self._p = Producer(
            {
                "bootstrap.servers": bootstrap,
                "enable.idempotence": True,
                "linger.ms": 50,
                "compression.type": "zstd",
            }
        )

    @classmethod
    def from_env(cls) -> "ChunkPublisher":
        return cls(
            bootstrap=os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                "localhost:9092",
            ),
            topic=os.getenv(
                "CHUNKS_TOPIC",
                "documents.chunks",
            ),
        )

    def publish(
        self,
        event: ChunkCreatedEvent,
    ) -> None:
        """
        Publish one ChunkCreatedEvent.
        """

        payload = json.dumps(
            event.to_dict(),
            ensure_ascii=False,
        ).encode("utf-8")

        log.info(
            "publishing chunk=%s topic=%s",
            event.chunk.extra["chunk_id"],
            self._topic,
        )

        self._p.produce(
            topic=self._topic,
            key=event.doc_id.encode("utf-8"),
            value=payload,
            on_delivery=self._ack,
        )

        # Trigger delivery callbacks.
        self._p.poll(0)

    def flush(
        self,
        timeout: float = 30.0,
    ) -> None:
        """
        Wait until every queued message has been delivered.
        """

        remaining = self._p.flush(timeout)

        if remaining:
            log.error(
                "%d chunk message(s) not delivered before timeout",
                remaining,
            )

    @staticmethod
    def _ack(err, msg) -> None:
        if err:
            log.error(
                "chunk publish failed: %s",
                err,
            )
            return

        log.info(
            "published chunk -> topic=%s partition=%s offset=%s",
            msg.topic(),
            msg.partition(),
            msg.offset(),
        )