"""System settings — one env-driven source of truth for the whole system."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import quote_plus
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"


def _get(*names: str, default: str | None = None) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default


@dataclass(frozen=True)
class Settings:
    # --- LLM ---
    gemini_api_key: str | None = field(default_factory=lambda: _get("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _get("GEMINI_MODEL", default="gemini-2.5-flash"))
    llm_max_attempts: int = 3
    llm_backoff_seconds: float = 1.5

    # --- Embedding (local BGE-M3) ---
    embedding_model: str = field(default_factory=lambda: _get("EMBEDDING_MODEL", default="BAAI/bge-m3"))
    embedding_dims: int = 1024

    # --- Vector store MCP ---
    # The retrieval agent talks to the vector store through an MCP server, not
    # a direct client. This lets us register MANY Qdrant databases (one per
    # language/corpus) behind one tool interface and route by language.
    vectorstore_mcp_url: str = field(default_factory=lambda: _get("VECTORSTORE_MCP_URL", default="inproc"))
    # "inproc" = call the MCP server in-process (no network); or an http url.

    sparse_vocab_path: str = field(default_factory=lambda: _get("SPARSE_VOCAB_PATH", default="./_store/sparse_vocab.json"))

    # --- Retrieval tuning ---
    max_chunk_budget: int = 300
    overfetch_factor: float = 2.0
    rrf_k: int = 60
    max_retries: int = 3
    min_confidence_to_stop: float = 0.6

    # --- State ---
    redis_url: str | None = quote_plus(field(default_factory=lambda: _get("REDIS_URL")))
    supabase_url: str | None = field(default_factory=lambda: _get("SUPABASE_URL"))
    supabase_key: str | None = field(default_factory=lambda: _get("SUPABASE_KEY"))
    session_ttl_seconds: int = 24 * 3600


settings = Settings()
