from __future__ import annotations

import argparse

import uvicorn

from ingestion_service.config import get_settings
from ingestion_service.observability import configure_logging
from ingestion_service.runtime import build_ingestion_runtime, build_vision_runtime


def _run(mode: str) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    runtime = (
        build_vision_runtime(settings) if mode == "vision-worker" else build_ingestion_runtime(settings)
    )
    thread = runtime.start_worker()
    try:
        uvicorn.run(
            runtime.app,
            host=settings.service_host,
            port=settings.service_port,
            log_level=settings.log_level.lower(),
            proxy_headers=True,
        )
    finally:
        runtime.stop(thread)


def main() -> None:
    parser = argparse.ArgumentParser(prog="ingestion-service")
    parser.add_argument("command", choices=("serve", "vision-worker"), nargs="?", default="serve")
    args = parser.parse_args()
    _run(args.command)


if __name__ == "__main__":
    main()
