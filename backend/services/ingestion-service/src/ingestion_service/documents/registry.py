from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ingestion_service.domain import DocumentUnit

from .base import DocumentReader, UnsupportedDocumentError


class ReaderRegistry:
    def __init__(self, readers: list[DocumentReader]) -> None:
        self._readers = readers

    def units(self, path: Path, content_type: str) -> Iterator[DocumentUnit]:
        for reader in self._readers:
            if reader.supports(path, content_type):
                yield from reader.units(path)
                return
        raise UnsupportedDocumentError(
            f"unsupported document type: extension={path.suffix!r}, content_type={content_type!r}"
        )

