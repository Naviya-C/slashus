"""POST /ingest -> pipeline.ingest -> chunks.

Left as a stub deliberately: ingestion in this system is driven by the Kafka
consumer (src/messaging/consumer.py), which already calls the pipeline
directly on `documents.uploaded` events. A synchronous HTTP /ingest route
would be a second entry point into the same pipeline and needs its own design
decision (sync vs fire-and-forget, request size limits, auth) rather than a
guess. main.py's /health is the only route wired up for now.
"""
