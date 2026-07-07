"""
ports/storage.py
================

PURPOSE
-------
The seam between the pipeline and wherever image bytes live. The pipeline stores
and retrieves images through THIS interface, never a specific backend -- so we
run/test locally against the filesystem now and swap in cloud object storage
(R2 / S3 / MinIO) later without touching pipeline code.

THE CONTRACT
------------
    put(key, data) -> str        store bytes at key, return a locator (path/url)
    get(key) -> bytes            read bytes back (used in tests / local serving)
    url(key) -> str              a locator to access it (file path now; signed URL in cloud)
    delete_prefix(prefix) -> int delete everything under a prefix, return count

KEY CONVENTION (per-user isolation)
-----------------------------------
Keys are user-prefixed so tenants never share storage and deletion is a single
prefix wipe:

    {user_id}/{doc_id}/images/{image_id}.{ext}

Use image_key() to build them consistently across every adapter.
"""

from __future__ import annotations

from typing import Protocol


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...
    def url(self, key: str) -> str: ...
    def delete_prefix(self, prefix: str) -> int: ...


def image_key(user_id: str, doc_id: str, image_id: str, ext: str) -> str:
    """Build the per-user storage key for an image (shared by all adapters)."""
    ext = ext.lower().lstrip(".")
    return f"{user_id}/{doc_id}/images/{image_id}.{ext}"