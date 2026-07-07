"""
ingestion/config.py
===================

PURPOSE
-------
Load tuning values from the environment (.env) with SAFE DEFAULTS, so the package
imports and runs even when no .env is present. Values can be overridden per-deploy
via environment variables.

    DEFAULT_TEXT_THRESHOLD      chars: min text for a page to count as digital
    DEFAULT_COVERAGE_THRESHOLD  fraction: min image coverage for a page to be a scan
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # dotenv optional; env vars still read if present


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
        "DEFAULT_TEXT_THRESHOLD": _get_int("DEFAULT_TEXT_THRESHOLD", 50),
        "DEFAULT_COVERAGE_THRESHOLD": _get_float("DEFAULT_COVERAGE_THRESHOLD", 0.5),
    }
