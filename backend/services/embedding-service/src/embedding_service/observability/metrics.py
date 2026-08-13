"""Prometheus metrics.

The previous service had none. "Retrieval got worse last Tuesday" was
answerable only by reading logs, and consumer lag -- the single most important
number for an ingest pipeline -- was not recorded anywhere.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# -- ingest ---------------------------------------------------------------

CHUNKS_INGESTED = Counter(
    "embedding_chunks_ingested_total", "Chunks embedded and written to Qdrant"
)
CHUNKS_SKIPPED = Counter(
    "embedding_chunks_skipped_total", "Chunks dropped by the quality gate", ["reason"]
)
INGEST_DURATION = Histogram(
    "embedding_ingest_batch_seconds",
    "Wall time to embed and upsert one batch",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)
BATCH_FAILURES = Counter(
    "embedding_batch_failures_total", "Batches that failed processing", ["stage"]
)
DLQ_MESSAGES = Counter(
    "embedding_dlq_messages_total", "Messages routed to the dead-letter topic", ["reason"]
)
CONSUMER_LAG = Gauge(
    "embedding_consumer_lag_messages",
    "Offset lag per partition on the chunks topic",
    ["partition"],
)

# -- search ---------------------------------------------------------------

SEARCH_DURATION = Histogram(
    "embedding_search_seconds",
    "End-to-end search latency",
    ["mode"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
SEARCH_HITS = Histogram(
    "embedding_search_hits",
    "Hits returned per search",
    ["mode"],
    buckets=(0, 1, 3, 5, 10, 20, 40, 80),
)
SEARCH_EMPTY = Counter("embedding_search_empty_total", "Searches returning nothing", ["reason"])

# -- rpc ------------------------------------------------------------------

GRPC_REQUESTS = Counter("embedding_grpc_requests_total", "gRPC calls handled", ["method", "code"])
GRPC_DURATION = Histogram(
    "embedding_grpc_duration_seconds",
    "gRPC handler latency",
    ["method"],
    buckets=(0.005, 0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10, 30),
)

# -- lifecycle ------------------------------------------------------------

COMPONENT_UP = Gauge(
    "embedding_component_up", "1 when a background component is healthy", ["component"]
)
