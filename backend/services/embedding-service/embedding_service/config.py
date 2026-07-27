"""
embedding_service/config.py
===================

PURPOSE
-------
Load tuning values from the environment (.env) with SAFE DEFAULTS, so the package
imports and runs even when no .env is present. Values can be overridden per-deploy
via environment variables.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    try:
        return int(val) if val is not None and val != "" else default
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    val = os.getenv(name)
    try:
        return float(val) if val is not None and val != "" else default
    except (TypeError, ValueError):
        return default


def load_env() -> dict:
    """Return config values, using env vars where set and safe defaults otherwise."""
    return {
        "QDRANT_CLUSTER_API": os.getenv("QDRANT_CLUSTER_API"),
        "QDRANT_CLUSTER_ENDPOINT": os.getenv("QDRANT_CLUSTER_ENDPOINT"),
        "QDRANT_COLLECTION": os.getenv("QDRANT_COLLECTION", "sinhala_books_v3"),
        "SPARSE_VOCAB_PATH": os.getenv("SPARSE_VOCAB_PATH", "./_store/sparse_vocab.json"),
    }
