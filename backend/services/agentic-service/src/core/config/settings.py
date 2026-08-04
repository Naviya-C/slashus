from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get(*names: str, default: str | None = None) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default


def _int(*names: str, default: int) -> int:
    v = _get(*names)
    if v is None:
        return default
    try:
        return int(v.strip())
    except ValueError:
        logging.getLogger(__name__).warning(
            "%s=%r is not an integer; using %d", names[0], v, default)
        return default


def _flag(*names: str, default: bool = False) -> bool:
    v = _get(*names)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    qwen_api_key: str | None = field(default_factory=lambda: _get("QWEN_API_KEY"))
    qwen_model: str = field(default_factory=lambda: _get("QWEN_MODEL", default="qwen3.6-plus"))

    gemini_api_key: str | None = field(default_factory=lambda: _get("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _get("GEMINI_MODEL", default="gemini-2.5-flash"))

    llm_max_attempts: int = 3
    llm_backoff_seconds: float = 1.5
    llm_max_output_tokens: int = 2048

    database_url: str | None = field(default_factory=lambda: _get("DATABASE_URL"))
    redis_url: str | None = field(default_factory=lambda: _get("REDIS_URL"))

    embedding_grpc_url: str = field(
        default_factory=lambda: _get("EMBEDDING_GRPC_URL", default="embedding-service:50051"))

    max_chunk_budget: int = 40
    rrf_k: int = 60
    overfetch_factor: float = 2.0

    max_tool_calls: int = field(default_factory=lambda: _int("MAX_TOOL_CALLS", default=5))
    max_retrieval_attempts: int = field(
        default_factory=lambda: _int("MAX_RETRIEVAL_ATTEMPTS", default=3))

    dev_mode: bool = field(default_factory=lambda: _flag("DEV_MODE", default=False))


settings = Settings()