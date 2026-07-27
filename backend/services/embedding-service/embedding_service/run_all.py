"""Container entrypoint: runs the Kafka consumer (the real workload) on a
background thread and the health-check API (api.py) on the main thread. See
ingestion-service/src/run_all.py for the same pattern and its trade-offs.
"""

import logging
import threading

import uvicorn

from embedding_service.api import app
from embedding_service.messaging.consumer import run as run_consumer

log = logging.getLogger("embedding.run_all")


def main() -> None:
    consumer_thread = threading.Thread(
        target=run_consumer, name="kafka-consumer", daemon=True
    )
    consumer_thread.start()
    log.info("kafka consumer thread started")

    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")


if __name__ == "__main__":
    main()
