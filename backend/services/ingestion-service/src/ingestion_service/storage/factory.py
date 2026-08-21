from __future__ import annotations

from pathlib import Path

from ingestion_service.config import Settings

from .base import ObjectStore
from .gcs import GCSStore
from .local import LocalStore


def create_stores(settings: Settings) -> tuple[ObjectStore, ObjectStore]:
    if settings.storage_backend == "local":
        root = Path(settings.local_storage_root)
        return LocalStore(root / "source"), LocalStore(root / "assets")
    return (
        GCSStore(settings.source_bucket, prefix=settings.storage_prefix),
        GCSStore(settings.asset_bucket, prefix=settings.storage_prefix),
    )

