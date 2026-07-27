"""
storage/gcs.py
==============

Google Cloud Storage implementation of the ObjectStore interface.
"""

from __future__ import annotations

from google.cloud import storage

from .base import ObjectStore


class GCSObjectStore(ObjectStore):
    """Google Cloud Storage backend."""

    def __init__(self, bucket: str):
        """
        Parameters
        ----------
        bucket:
            Name of the GCS bucket.
        """
        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket)

    def put(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """
        Store an object in Google Cloud Storage.
        """
        blob = self._bucket.blob(key)

        blob.upload_from_string(
            data,
            content_type=content_type,
        )

    def get(
        self,
        *,
        key: str,
    ) -> bytes:
        """
        Download an object.

        Raises
        ------
        FileNotFoundError
            If the object does not exist.
        """
        blob = self._bucket.blob(key)

        if not blob.exists():
            raise FileNotFoundError(key)

        return blob.download_as_bytes()

    def exists(
        self,
        *,
        key: str,
    ) -> bool:
        """
        Return True if the object exists.
        """
        blob = self._bucket.blob(key)
        return blob.exists()

    def delete(
        self,
        *,
        key: str,
    ) -> None:
        """
        Delete an object.

        Missing objects are ignored.
        """
        blob = self._bucket.blob(key)

        if blob.exists():
            blob.delete()