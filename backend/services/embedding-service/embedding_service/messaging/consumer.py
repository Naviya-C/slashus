"""
messaging/consumer.py  (EMBEDDING service)
==========================================

Consumes ChunkCreatedEvent messages, embeds a single chunk, and upserts it into
Qdrant.

Pipeline

    documents.chunks
            │
            ▼
     ChunkCreatedEvent
            │
            ▼
     embed_and_store_chunk()
            │
            ▼
         Qdrant

DELIVERY
--------
Manual commit after the upsert succeeds.

Kafka may redeliver a chunk if the consumer crashes before committing.
This is safe because point_id is deterministic (uuid5(chunk_id)), so
Qdrant simply overwrites the existing point.
"""

from __future__ import annotations

import json
import logging
import os

from confluent_kafka import Consumer
from qdrant_client import QdrantClient

from contracts import ChunkCreatedEvent

from embedding_service.embedding.store import (
    embed_and_store_chunk,
    EmbedDeps,
)

from embedding_service.adapter import (
    LocalEmbedder,
    SinhalaSparseEncoder,
)

from embedding_service.config import load_env

log = logging.getLogger(__name__)


def build_deps(cfg=None) -> EmbedDeps:
    cfg = cfg or load_env()
    return EmbedDeps(
        dense=LocalEmbedder(),
        sparse=SinhalaSparseEncoder(
            cfg["SPARSE_VOCAB_PATH"],
        ),
        client=QdrantClient(
            url=cfg["QDRANT_CLUSTER_ENDPOINT"],
            api_key=cfg["QDRANT_CLUSTER_API"],
            timeout=120,
        ),
    )


def _handle(
    event: ChunkCreatedEvent,
    *,
    deps: EmbedDeps,
) -> None:

    embed_and_store_chunk(
        chunk=event.chunk,
        collection=event.collection,
        deps=deps,
        #require_title=event.require_title,
    )

    log.info(
        "embedded chunk=%s doc=%s",
        event.chunk.extra["chunk_id"],
        event.doc_id,
    )


def run(deps: EmbedDeps | None = None) -> None:

    logging.basicConfig(level=logging.INFO)

    deps = deps or build_deps()

    consumer = Consumer(
        {
            "bootstrap.servers": os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                "localhost:9092",
            ),
            "group.id": os.getenv(
                "EMBEDDING_GROUP",
                "embedding",
            ),
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            "max.poll.interval.ms": 900_000,
        }
    )

    topic = os.getenv(
        "CHUNKS_TOPIC",
        "documents.chunks",
    )

    consumer.subscribe([topic])

    log.info(
        "embedding consumer started topic=%s",
        topic,
    )

    try:

        while True:

            msg = consumer.poll(1.0)

            if msg is None:
                continue

            if msg.error():
                log.error(
                    "consume error: %s",
                    msg.error(),
                )
                continue

            event = None

            try:

                event = ChunkCreatedEvent.from_dict(
                    json.loads(msg.value())
                )

                _handle(
                    event,
                    deps=deps,
                )

                consumer.commit(msg)

            except Exception:

                log.exception(
                    "embedding failed chunk=%s",
                    event.chunk.extra["chunk_id"]
                    if event
                    else "<unknown>",
                )

    finally:

        consumer.close()


if __name__ == "__main__":
    run()