"""
embedding_service/run_all.py
============================

Container entrypoint. Three things in one process:

    Kafka consumer   background thread   embeds and stores incoming chunks
    gRPC server      background thread   serves search to agentic-service
    health API       main thread         liveness for Docker

One process because they SHARE one BGE-M3 instance (~2.2 GB) and one sparse
vocab. Separate containers would load the model twice, which on an 8 GB VM
already running Kafka and six other services is the difference between working
and OOM — and would reintroduce the stale-vocab problem the consolidation
removes.

CRASH GUARDS
------------
Every background thread exits the PROCESS on an unhandled exception rather
than dying quietly. Without this a dead thread sits behind a healthy HTTP
probe: the container reports fine and nothing works. That has cost real
debugging time here more than once, and it matters more now that search runs
here — a dead gRPC thread means chat hangs while /health keeps saying ok.

With `restart: unless-stopped`, a crash now surfaces as a restart loop.
"""

from __future__ import annotations

import logging
import os
import threading

import uvicorn

from embedding_service.api import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("embedding.run_all")

GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
HTTP_PORT = int(os.getenv("HTTP_PORT", "8004"))


def _guard(name: str, fn) -> None:
    """Run fn; kill the process if it raises.

    os._exit rather than sys.exit: this runs on a non-main thread, where
    SystemExit unwinds only that thread and leaves the process alive — which
    is exactly the silent death being fixed.
    """
    try:
        fn()
    except Exception:
        log.exception("%s died — exiting so the container restarts", name)
        os._exit(1)


def main() -> None:
    from embedding_service.grpc_server import serve_forever
    from embedding_service.messaging.consumer import build_deps
    from embedding_service.messaging.consumer import run as run_consumer

    deps = build_deps()
    log.info("embedder and sparse vocab loaded")

    threading.Thread(
        target=_guard, args=("kafka consumer", lambda: run_consumer(deps)),
        name="kafka-consumer", daemon=True,
    ).start()
    log.info("kafka consumer thread started")

    threading.Thread(
        target=_guard, args=("grpc server", lambda: serve_forever(deps, GRPC_PORT)),
        name="grpc-server", daemon=True,
    ).start()
    log.info("grpc server thread started on :%d", GRPC_PORT)

    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT, log_level="info")


if __name__ == "__main__":
    main()
