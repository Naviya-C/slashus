"""
adapters/gcs_storage.py
=======================

PURPOSE
-------
Storage implemented on Google Cloud Storage. Implements the SAME Storage port
as LocalStorage, so switching local <-> cloud is one line in deps.py and the
pipeline never knows the difference.

WHY THE KEY MATTERS MORE THAN THE URL
-------------------------------------
put() returns a URL, and the pipeline writes it into the image chunk's
`storage_url` extra -> Qdrant payload. But signed URLs EXPIRE, and a payload
written today may be read months from now.

So the payload must also carry `storage_key`. The retrieval agent then calls
storage.url(payload["storage_key"]) to mint a fresh URL on demand, instead of
trusting a stale one. Store the key; treat the URL as a cache.

MULTI-TENANCY
-------------
This adapter is key-agnostic — isolation comes from the KEY CONVENTION in
ports/storage.py:

    {user_id}/{doc_id}/images/{image_id}.{ext}     via image_key()
    vocab/{collection}.json                        shared build artifact

_blob_name() rejects traversal (".." or leading "/") so a malformed doc_id
cannot escape into another tenant's prefix. That guard assumes user_id itself
is trusted — it comes from the gateway-verified token, never from the client.

Requires:
    pip install google-cloud-storage
Auth (either):
    - GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    - or ambient credentials on GCE/Cloud Run (workload identity)

URL MODES
---------
    signed_url_ttl > 0  -> V4 signed URLs, private bucket (RECOMMENDED).
    signed_url_ttl = 0  -> plain public URLs; bucket objects must be publicly
                           readable (fine for non-sensitive textbook figures).

NOTE: a signed URL is a bearer token in link form — anyone holding it can read
the object until it expires. Keep the TTL short and re-sign, rather than
minting week-long URLs.
"""

from __future__ import annotations

import datetime
import logging
import mimetypes

from src.ingestion.ports.storage import StorageKeyNotFound


log = logging.getLogger(__name__)


# Default TTL is deliberately short: the agent re-signs from storage_key when
# it needs a fresh link, so long-lived URLs buy nothing but risk.
_DEFAULT_TTL = 3600

class GCSStorage:
    """Storage port backed by a Google Cloud Storage bucket."""

    def __init__(
        self,
        bucket_name: str,
        *,
        prefix: str = "",                    # optional root folder in the bucket
        signed_url_ttl: int = _DEFAULT_TTL,  # seconds; 0 = public URLs
    ) -> None:
        from google.cloud import storage  # optional dep; imported lazily

        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name)
        self._prefix = prefix.strip("/")
        self._ttl = signed_url_ttl

    # ------------------------------------------------------------------

    def _blob_name(self, key: str) -> str:
        """Map a logical key to a blob name, refusing anything that could
        escape its prefix."""
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError(f"unsafe storage key: {key!r}")
        return f"{self._prefix}/{key}" if self._prefix else key

    # ------------------------------------------------------------------

    def put(self, key: str, data: bytes) -> str:
        """Upload bytes; returns a URL. Persist the KEY alongside it — the URL
        expires, the key does not."""
        blob = self._bucket.blob(self._blob_name(key))
        # Infer content type from the extension so browsers render images
        # inline instead of downloading them as octet-stream.
        content_type, _ = mimetypes.guess_type(key)
        blob.upload_from_string(data, content_type=content_type)
        return self.url(key)

    def get(self, key: str) -> bytes:
        """Read bytes back. Raises StorageKeyNotFound if the key is absent."""
        from google.cloud import exceptions  # lazy, same as the client import

        blob = self._bucket.blob(self._blob_name(key))
        try:
            return blob.download_as_bytes()
        except exceptions.NotFound as exc:
            raise StorageKeyNotFound(key) from exc

    def exists(self, key: str) -> bool:
        """Cheap existence check — lets callers branch without catching.

        Used by the sparse-vocab loader: on the very first ingestion run there
        is no vocab yet, and that is a normal state, not an error.
        """
        return self._bucket.blob(self._blob_name(key)).exists(self._client)

    def url(self, key: str, *, ttl: int | None = None) -> str:
        """Signed URL (private bucket) or public URL (ttl=0).

        Pass `ttl` to override the instance default — e.g. a short-lived link
        minted per request when the agent re-signs from a stored storage_key.
        """
        blob = self._bucket.blob(self._blob_name(key))
        effective = self._ttl if ttl is None else ttl
        if effective <= 0:
            return blob.public_url
        return blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=effective),
            method="GET",
        )

    def delete_prefix(self, prefix: str) -> int:
        """Delete everything under a key prefix (one user / one doc wipe).

        Guards against an empty prefix, which would otherwise resolve to the
        bucket root and delete every object in it.
        """
        if not prefix or not prefix.strip("/"):
            raise ValueError("refusing to delete an empty prefix")

        blob_prefix = self._blob_name(prefix)
        count = 0
        for blob in self._client.list_blobs(self._bucket, prefix=blob_prefix):
            try:
                blob.delete()
                count += 1
            except Exception:
                log.warning("failed deleting gs://%s", blob.name, exc_info=True)
        log.info("deleted %d object(s) under %s", count, blob_prefix)
        return count