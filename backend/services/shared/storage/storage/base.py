"""
storage/base.py
===============

Abstract interface for object storage backends.

Every storage implementation (Local, GCS, S3, MinIO, etc.)
must implement this interface.

The upload service interacts only with ObjectStore and never
depends on a specific storage provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ObjectStore(ABC):
    """Abstract object storage backend."""

    @abstractmethod
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
            Logical object key
            Example:
                user_id/doc_id/source.pdf

        data:
            Object bytes.

        content_type:
            MIME type.
            Example:
                application/pdf
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        *,
        key: str,
    ) -> bool:
        """
        Return True if the object exists.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        *,
        key: str,
    ) -> None:
        """
        Delete an object.

        Should succeed even if the object does not exist.
        """
        raise NotImplementedError