"""
adapters/local_storage.py
=========================

PURPOSE
-------
Storage implemented on the local filesystem. Lets the whole image pipeline run
and be tested end to end with no cloud account. The cloud adapter (R2 / S3 /
MinIO) implements the SAME Storage port later; swapping is a one-line change.

Keys map to paths under a base directory: key "user_a/doc_1/images/img.png"
becomes <base>/user_a/doc_1/images/img.png. Per-user isolation falls out of the
key layout for free (each user is a top-level folder).

SAFETY
------
Keys are validated to prevent path traversal (no '..', no absolute paths), so a
crafted key can never write outside the base directory.
"""

from __future__ import annotations

import shutil
from pathlib import Path


class LocalStorage:
    """Filesystem-backed Storage. Base dir holds all objects, keyed by path."""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        if not key or key.startswith("/") or "\\" in key or ".." in key.split("/"):
            raise ValueError(f"unsafe storage key: {key!r}")
        path = (self._base / key).resolve()
        base = self._base.resolve()
        if path != base and base not in path.parents:
            raise ValueError(f"key escapes base dir: {key!r}")
        return path

    def put(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return self.url(key)

    def get(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def url(self, key: str) -> str:
        # local locator; the cloud adapter returns a signed URL here instead
        return self._resolve(key).as_uri()

    def delete_prefix(self, prefix: str) -> int:
        base = self._base.resolve()
        if not base.exists():
            return 0
        count = 0
        for p in list(base.rglob("*")):
            if p.is_file() and p.relative_to(base).as_posix().startswith(prefix):
                p.unlink()
                count += 1
        # tidy up now-empty directories
        for d in sorted((d for d in base.rglob("*") if d.is_dir()), reverse=True):
            try:
                d.rmdir()
            except OSError:
                pass
        return count