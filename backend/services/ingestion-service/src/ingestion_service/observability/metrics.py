from prometheus_client import Counter, Gauge, Histogram

DOCUMENTS_COMPLETED = Counter("ingestion_documents_completed_total", "Completed documents")
DOCUMENTS_FAILED = Counter(
    "ingestion_documents_failed_total", "Failed document attempts", ["reason"]
)
DOCUMENT_SECONDS = Histogram(
    "ingestion_document_seconds",
    "End-to-end extraction and publication time",
    buckets=(1, 2.5, 5, 10, 30, 60, 120, 300, 600, 1200),
)
UNITS_PROCESSED = Counter("ingestion_units_processed_total", "Pages, slides, or sheets processed")
CHUNKS_PUBLISHED = Counter("ingestion_chunks_published_total", "Chunk events published")
IMAGES_QUEUED = Counter("ingestion_images_queued_total", "Images queued for optional enrichment")
DLQ_DOCUMENTS = Counter("ingestion_dlq_documents_total", "Documents sent to DLQ", ["reason"])
CONSUMER_LAG = Gauge(
    "ingestion_consumer_lag_messages", "Upload-topic consumer lag", ["partition"]
)
VISION_REQUESTS = Counter("ingestion_vision_requests_total", "Vision requests", ["outcome"])
VISION_CIRCUIT_OPEN = Gauge("ingestion_vision_circuit_open", "1 while vision circuit is open")

