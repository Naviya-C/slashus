"""System settings — one env-driven source of truth for the whole system."""

from __future__ import annotations

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


def _flag(*names: str, default: bool = False) -> bool:
    """Parse a boolean env var.

    Explicit set membership rather than bool(): `bool("false")` is True, which
    is the single most common way a feature flag ends up permanently on.
    """
    v = _get(*names)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # --- LLM: Qwen ------------------------------------------------
    qwen_api_key: str | None = field(default_factory=lambda: _get("QWEN_API_KEY"))
    qwen_model: str = field(default_factory=lambda: _get("QWEN_MODEL", default="qwen3.6-plus"))

    # --- LLM: Gemini (retained for retrieval understanding + evaluator) ---
    gemini_api_key: str | None = field(default_factory=lambda: _get("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _get("GEMINI_MODEL", default="gemini-2.5-flash"))

    llm_max_attempts: int = 3
    llm_backoff_seconds: float = 1.5
    llm_max_output_tokens: int = 2048

    # --- Embedding (local BGE-M3) ---------------------------------------

    # --- Vector store MCP ------------------------------------------------
    # embedding-service owns Qdrant, BGE-M3 and the sparse vocab. This is the
    # only way search reaches them.
    embedding_grpc_url: str = field(
        default_factory=lambda: _get("EMBEDDING_GRPC_URL", default="embedding-service:50051"))

    # --- Retrieval tuning ------------------------------------------------
    max_chunk_budget: int = 300
    overfetch_factor: float = 2.0
    rrf_k: int = 60
    max_retries: int = 3
    min_confidence_to_stop: float = 0.6

    # Reranking is OFF by default. Cause the rate limiting
    enable_reranking: bool = field(default_factory=lambda: _flag("ENABLE_RERANKING", default=False))
    rerank_top_k: int = 30

    # --- Persistence -----------------------------------------------------
    database_url: str | None = field(default_factory=lambda: _get("DATABASE_URL"))
    redis_url: str | None = field(default_factory=lambda: _get("REDIS_URL"))

    # --- Dev mode --------------------------------------------------------
    # Gates raw chunk exposure. Chunks are full passages of copyrighted
    # textbooks; returning them to a browser lets any logged-in user
    # reconstruct the corpus a page at a time. Never true on a deployed host.
    dev_mode: bool = field(default_factory=lambda: _flag("DEV_MODE", default=False))


settings = Settings()
