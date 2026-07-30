"""
messaging/consumer.py
=====================

Consumes document upload events, runs the ingestion pipeline, and publishes
ONE ChunkCreatedEvent per chunk.

Pipeline

    documents.uploaded
            │
            ▼
       storage.get()
            │
            ▼
         ingest()
            │
            ▼
     ChunkCreatedEvent x N
            │
            ▼
     documents.chunks

Delivery
--------
Manual offset commit.

Offsets are committed ONLY AFTER every chunk has been successfully published.
If ingestion fails, Kafka redelivers the upload event.

Chunk events are idempotent because chunk_ids are deterministic.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile

from confluent_kafka import Consumer

from contracts import (
    DocUploaded,
    ChunkCreatedEvent,
)

from src.messaging.producer import ChunkPublisher
from src.ingestion.pipeline.ingest import ingest
from src.ingestion.pipeline.deps import default_deps

from storage.factory import create_store
from src.ingestion.config import load_env

log = logging.getLogger(__name__)

source_storage = create_store(os.getenv("SOURCE_BUCKET"))
image_storage = create_store(os.getenv("IMAGE_BUCKET"))

def _fully_scanned(chunks) -> bool:
    """
    True when every produced chunk came from OCR.
    """

    return bool(chunks) and all(
        c.extra.get("ocr")
        for c in chunks
    )


def _handle(
    evt: DocUploaded,
    *,
    storage,
    deps,
    publisher: ChunkPublisher,
    collection: str,
) -> None:

    log.info("received document: %s", evt.doc_id)

    data = storage.get(
        key=evt.storage_key,
    )

    log.info(
        "fetched pdf: doc_id=%s bytes=%d",
        evt.doc_id,
        len(data),
    )

    with tempfile.NamedTemporaryFile(
        suffix=".pdf",
    ) as tmp:

        tmp.write(data)
        tmp.flush()

        chunks = ingest(
            tmp.name,
            user_id=evt.user_id,
            doc_id=evt.doc_id,
            source_name=evt.source_name,
            deps=deps,
        )

    require_title = not _fully_scanned(chunks)

    #
    # Publish ONE Kafka message per chunk
    #
    for chunk in chunks:

        publisher.publish(
            ChunkCreatedEvent(
                doc_id=evt.doc_id,
                user_id=evt.user_id,
                source_name=evt.source_name,
                collection=collection,
                require_title=require_title,
                chunk=chunk,
            )
        )

    publisher.flush()

    log.info(
        "published %d chunks for %s",
        len(chunks),
        evt.doc_id,
    )


def run() -> None:

    logging.basicConfig(level=logging.INFO)

    cfg = load_env()

    collection = os.getenv(
        "QDRANT_COLLECTION",
        "sinhala_books_v3",
    )

    storage = create_store()

    deps = default_deps(
        gemini_key=os.getenv("GEMINI_API_KEY"),
        storage=image_storage,
    )

    publisher = ChunkPublisher.from_env()

    topic = os.getenv("UPLOAD_TOPIC", "documents.uploaded")

    group = os.getenv("INGESTION_GROUP", "ingestion")

    bootstrap = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9092",
    )

    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": group,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )

    consumer.subscribe([topic])

    log.info(
        "consumer started topic=%s group=%s",
        topic,
        group,
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

            evt = None
            payload = None

            try:

                #
                # Decode Kafka payload
                #
                payload = json.loads(msg.value())

                log.info("========== RECEIVED MESSAGE ==========")
                log.info("Topic      : %s", msg.topic())
                log.info("Partition  : %s", msg.partition())
                log.info("Offset     : %s", msg.offset())
                log.info("Key        : %r", msg.key())
                log.info("Payload    : %r", payload)
                log.info("Keys       : %s", list(payload.keys()))
                log.info("======================================")

                #
                # Deserialize event
                #
                evt = DocUploaded.from_dict(payload)

                #
                # Process document
                #
                _handle(
                    evt,
                    storage=source_storage,
                    deps=deps,
                    publisher=publisher,
                    collection=collection,
                )

                #
                # Commit ONLY after successful processing
                #
                consumer.commit(msg)

                log.info(
                    "committed offset=%s",
                    msg.offset(),
                )

            except Exception:

                log.exception(
                    "ingest failed\n"
                    "offset=%s\n"
                    "payload=%r",
                    msg.offset(),
                    payload,
                )

    finally:

        consumer.close()


if __name__ == "__main__":
    run()
