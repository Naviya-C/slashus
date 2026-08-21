from __future__ import annotations

import shutil
from pathlib import Path


class LocalStore:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("unsafe storage key")
        candidate = (self._root / key).resolve()
        if self._root not in candidate.parents and candidate != self._root:
            raise ValueError("storage key escaped local root")
        return candidate

    def download_to_file(self, key: str, destination: Path) -> int:
        source = self._path(key)
        if not source.is_file():
            raise FileNotFoundError(key)
        shutil.copyfile(source, destination)
        return destination.stat().st_size

    def upload_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        destination = self._path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    def download_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

