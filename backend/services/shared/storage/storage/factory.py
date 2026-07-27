"""
storage/factory.py
==================

Factory for creating the configured object storage backend.

Supported providers
-------------------
- local
- gcs
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import ObjectStore
from .gcs import GCSObjectStore
from .local import LocalObjectStore

 
def create_store() -> ObjectStore:
    """
    Create and return the configured storage backend.

    Environment variables
    ---------------------
    STORAGE_PROVIDER
        local (default)
        gcs

    LOCAL_STORAGE_ROOT
        Root directory for LocalObjectStore.

    GCS_BUCKET
        Bucket name for Google Cloud Storage.
    """
    provider = os.getenv("STORAGE_PROVIDER", "local").lower()

    match provider:
        case "local":
            root = Path(
                os.getenv(
                    "LOCAL_STORAGE_ROOT",
                    "./data/uploads",
                )
            )

            return LocalObjectStore(root)

        case "gcs":
            bucket = os.environ["GCS_BUCKET"]

            return GCSObjectStore(bucket)

        case _:
            raise ValueError(
                f"Unsupported STORAGE_PROVIDER: {provider!r}"
            )