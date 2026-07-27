"""Container entrypoint: runs the Kafka consumer and the health-check API
together in one process, so the container has a single PID (correct signal
handling, one thing for `docker compose ps` to report on) while still
answering GET /health for anyone probing the port docker-compose exposes.

The consumer is the real workload and runs on its own thread; uvicorn runs on
the main thread. If the consumer thread dies, the container stays "healthy"
by HTTP but is no longer consuming — that's a real limitation of bolting an
HTTP surface onto a worker after the fact. Logs are the source of truth for
consumer health until job-status tracking (see api/main.py) exists.
"""

import logging
import threading

import uvicorn

from src.ingestion.api.main import app
from src.messaging.consumer import run as run_consumer

log = logging.getLogger("ingestion.run_all")


def main() -> None:
    consumer_thread = threading.Thread(
        target=run_consumer, name="kafka-consumer", daemon=True
    )
    consumer_thread.start()
    log.info("kafka consumer thread started")

    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")


if __name__ == "__main__":
    main()
