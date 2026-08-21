from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from ingestion_service.domain import DocumentUnit


class DocumentReader(Protocol):
    def supports(self, path: Path, content_type: str) -> bool: ...

    def units(self, path: Path) -> Iterator[DocumentUnit]: ...


class UnsupportedDocumentError(ValueError):
    pass


class DocumentLimitError(ValueError):
    pass

