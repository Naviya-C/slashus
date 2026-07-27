"""
storage/local.py
================

Local filesystem implementation of the ObjectStore interface.

This backend is intended for local development and testing.

Objects are stored under a configurable root directory while
preserving the same logical object keys used by cloud storage.

Example
-------
root = /data/uploads

key:
    user123/doc456/source.pdf

stored as:
    /data/uploads/user123/doc456/source.pdf
"""

from __future__ import annotations

from pathlib import Path

from .base import ObjectStore


class LocalObjectStore(ObjectStore):
    """Filesystem-backed object storage."""

    def __init__(self, root: str | Path):
        self._root = Path(root)

        # Create storage root if it doesn't already exist.
        self._root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def put(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """
        Store an object.

        Parameters
        ----------
        key:
            Logical storage key.
        data:
            File bytes.
        content_type:
            Ignored for local storage but accepted to keep the
            interface identical to cloud implementations.
        """
        path = self._path(key)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(data)

    def get(
        self,
        *,
        key: str,
    ) -> bytes:
        """
        Retrieve an object.

        Raises
        ------
        FileNotFoundError
            If the object does not exist.
        """
        path = self._path(key)

        if not path.exists():
            raise FileNotFoundError(key)

        return path.read_bytes()

    def exists(
        self,
        *,
        key: str,
    ) -> bool:
        """Return True if the object exists."""
        return self._path(key).exists()

    def delete(
        self,
        *,
        key: str,
    ) -> None:
        """
        Delete an object.

        Missing files are ignored.
        """
        path = self._path(key)

        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def _path(self, key: str) -> Path:
        """
        Convert a logical object key into a filesystem path.

        Example
        -------
        key:
            user123/doc456/source.pdf

        becomes

            /data/uploads/user123/doc456/source.pdf
        """
        return self._root / Path(key)