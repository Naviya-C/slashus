"""
Consumes ChunkCreatedEvent messages, embeds them in BATCHES, and upserts into
Qdrant.

    documents.chunks -> [up to N events] -> embed batch -> Qdrant -> commit

DELIVERY
--------
At-least-once with idempotent writes. Offsets are committed only after the
WHOLE batch has landed, so a crash mid-batch redelivers up to N chunks. That is
safe because point_id is uuid5(chunk_id): a replay overwrites its own point.

VOCAB DURABILITY
----------------
The encoder no longer writes on every chunk. It writes when enough new terms
have accumulated, and this loop forces a flush whenever the topic goes quiet and
on shutdown -- otherwise a crash loses whatever terms had not yet tripped the
threshold, and those chunks' sparse vectors reference indices no query can ever
produce again.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict

from confluent_kafka import Consumer
from qdrant_client import QdrantClient

from contracts import ChunkCreatedEvent

from embedding_service.adapter import LocalEmbedder, SinhalaSparseEncoder
from embedding_service.config import load_env
from embedding_service.embedding.store import EmbedDeps, embed_and_store_chunks

log = logging.getLogger(__name__)

_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))
_BATCH_TIMEOUT = float(os.getenv("EMBED_BATCH_TIMEOUT", "2.0"))


def build_deps(cfg=None) -> EmbedDeps:
    """
    --- Construct the shared dependencies.---

    Public and callable with no arguments so run_all.py builds ONE instance and
    hands it to both the consumer and the gRPC server. Two instances would mean
    two BGE-M3 models (~2.2 GB each) in one process, and two views of the sparse
    vocab -- the reader's going stale the moment ingest appends a term.
    """
    cfg = cfg or load_env()
    return EmbedDeps(
        dense=LocalEmbedder(),
        sparse=SinhalaSparseEncoder(cfg["SPARSE_VOCAB_PATH"]),
        client=QdrantClient(
            url=cfg["QDRANT_CLUSTER_ENDPOINT"],
            api_key=cfg["QDRANT_CLUSTER_API"],
            timeout=120,
        ),
    )


def _decode(msgs) -> list[ChunkCreatedEvent]:
    events: list[ChunkCreatedEvent] = []
    for msg in msgs:
        if msg.error():
            log.error("consume error: %s", msg.error())
            continue
        try:
            events.append(ChunkCreatedEvent.from_dict(json.loads(msg.value())))
        except Exception:
            log.exception(
                "undecodable message dropped: partition=%s offset=%s",
                msg.partition(),
                msg.offset(),
            )
    return events


def run(deps: EmbedDeps | None = None) -> None:
    logging.basicConfig(level=logging.INFO)

    deps = deps or build_deps()

    consumer = Consumer(
        {
            "bootstrap.servers": os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
            ),
            "group.id": os.getenv("EMBEDDING_GROUP", "embedding"),
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            # Generous: a full batch of Sinhala chunks through BGE-M3 on CPU is
            # slow, and exceeding this triggers a rebalance mid-batch.
            "max.poll.interval.ms": 900_000,
        }
    )

    topic = os.getenv("CHUNKS_TOPIC", "documents.chunks")
    consumer.subscribe([topic])
    log.info(
        "embedding consumer started topic=%s batch=%d", topic, _BATCH_SIZE
    )

    try:
        while True:
            msgs = consumer.consume(
                num_messages=_BATCH_SIZE, timeout=_BATCH_TIMEOUT
            )

            if not msgs:
                # Idle. Nothing is arriving, so this is the cheapest possible
                # moment to make the vocab durable.
                deps.sparse.save(force=True)
                continue

            events = _decode(msgs)
            if not events:
                consumer.commit(asynchronous=False)
                continue

            groups: dict[tuple[str, bool], list] = defaultdict(list)
            for e in events:
                groups[(e.collection, e.require_title)].append(e.chunk)

            try:
                stored = 0
                for (collection, require_title), chunks in groups.items():
                    stored += embed_and_store_chunks(
                        chunks=chunks,
                        collection=collection,
                        deps=deps,
                        require_title=require_title,
                    )

                consumer.commit(asynchronous=False)
                log.info(
                    "committed batch: %d events, %d stored", len(events), stored
                )

            except Exception:
                log.exception(
                    "batch failed (%d events); offsets NOT committed, "
                    "Kafka will redeliver",
                    len(events),
                )

    finally:
        try:
            deps.sparse.save(force=True)
        except Exception:
            log.exception("final vocab flush failed")
        consumer.close()


if __name__ == "__main__":
    run()