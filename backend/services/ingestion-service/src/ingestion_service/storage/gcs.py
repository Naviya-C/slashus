from __future__ import annotations

import mimetypes
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import storage


class GCSStore:
    def __init__(self, bucket_name: str, *, prefix: str = "") -> None:
        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name)
        self._prefix = prefix.strip("/")

    def _name(self, key: str) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("unsafe storage key")
        return f"{self._prefix}/{key}" if self._prefix else key

    def download_to_file(self, key: str, destination: Path) -> int:
        blob = self._bucket.blob(self._name(key))
        try:
            blob.download_to_filename(str(destination))
        except NotFound as exc:
            raise FileNotFoundError(key) from exc
        return destination.stat().st_size

    def upload_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        blob = self._bucket.blob(self._name(key))
        guessed, _ = mimetypes.guess_type(key)
        blob.upload_from_string(data, content_type=content_type or guessed)

    def download_bytes(self, key: str) -> bytes:
        blob = self._bucket.blob(self._name(key))
        try:
            return blob.download_as_bytes()
        except NotFound as exc:
            raise FileNotFoundError(key) from exc


def asset_key(user_id: str, doc_id: str, digest: str, extension: str) -> str:
    clean_ext = extension.lower().lstrip(".") or "bin"
    return f"{user_id}/{doc_id}/assets/{digest}.{clean_ext}"

