"""
Structured logging.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from agentic_service.config.settings import ObservabilitySettings


def configure_logging(cfg: ObservabilitySettings, *, service: str, version: str) -> None:
    level = getattr(logging, cfg.log_level)

    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if cfg.log_format == "json"
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            *shared,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(processor=renderer, foreign_pre_chain=shared)
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for noisy in ("httpx", "httpcore", "urllib3", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.contextvars.bind_contextvars(service=service, version=version)


__all__ = ["bind_contextvars", "clear_contextvars", "configure_logging"]
