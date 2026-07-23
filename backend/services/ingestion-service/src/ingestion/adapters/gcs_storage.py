"""
adapters/gcs_storage.py
=======================

PURPOSE
-------
Storage implemented on Google Cloud Storage. Implements the SAME Storage port
as LocalStorage, so switching local <-> cloud is one line in deps.py and the
pipeline never knows the difference.

WHY THE URL MATTERS
-------------------
put() returns a URL, and the pipeline writes it into the image chunk's
`storage_url` extra -> Qdrant payload. That's the link the retrieval agent
uses to CONNECT the image: when a retrieved chunk is type "image", the agent
reads payload["storage_url"] and can show the picture directly, without ever
holding GCS credentials itself.

Requires:
    pip install google-cloud-storage
Auth (either):
    - GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    - or ambient credentials on GCE/Cloud Run (workload identity)

URL MODES
---------
    signed_url_ttl > 0  -> V4 signed URLs, private bucket (RECOMMENDED).
                           NOTE: signed URLs expire; if the agent reads
                           payloads long after ingest, have the agent call
                           storage.url(payload["storage_key"]) to re-sign
                           instead of trusting the stored URL forever.
    signed_url_ttl = 0  -> plain public URLs; bucket objects must be
                           publicly readable (fine for non-sensitive
                           textbook figures, zero re-signing needed).
"""

from __future__ import annotations

import datetime
import logging

log = logging.getLogger(__name__)


class GCSStorage:
    """Storage port backed by a Google Cloud Storage bucket."""

    def __init__(
        self,
        bucket_name: str,
        *,
        prefix: str = "",              # optional root folder inside the bucket
        signed_url_ttl: int = 7 * 24 * 3600,   # seconds; 0 = public URLs
    ) -> None:
        from google.cloud import storage  # optional dep; imported lazily

        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name)
        self._prefix = prefix.strip("/")
        self._ttl = signed_url_ttl

    # ------------------------------------------------------------------

    def _blob_name(self, key: str) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError(f"unsafe storage key: {key!r}")
        return f"{self._prefix}/{key}" if self._prefix else key

    # ------------------------------------------------------------------

    def put(self, key: str, data: bytes) -> str:
        """Upload bytes; returns the URL that goes into the Qdrant payload."""
        blob = self._bucket.blob(self._blob_name(key))
        blob.upload_from_string(data)  # content type inferred from extension
        return self.url(key)

    def get(self, key: str) -> bytes:
        return self._bucket.blob(self._blob_name(key)).download_as_bytes()

    def url(self, key: str) -> str:
        """Signed URL (private bucket) or public URL (ttl=0)."""
        blob = self._bucket.blob(self._blob_name(key))
        if self._ttl <= 0:
            return blob.public_url
        return blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=self._ttl),
            method="GET",
        )

    def delete_prefix(self, prefix: str) -> int:
        """Delete everything under a key prefix (one user / one doc wipe)."""
        blob_prefix = self._blob_name(prefix)
        blobs = list(self._client.list_blobs(self._bucket, prefix=blob_prefix))
        count = 0
        for blob in blobs:
            try:
                blob.delete()
                count += 1
            except Exception:
                log.warning("failed deleting gs://%s", blob.name, exc_info=True)
        return count
