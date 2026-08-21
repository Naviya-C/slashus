from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    def download_to_file(self, key: str, destination: Path) -> int: ...

    def upload_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> None: ...

    def download_bytes(self, key: str) -> bytes: ...

