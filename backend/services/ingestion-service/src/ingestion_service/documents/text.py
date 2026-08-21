from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from pathlib import Path

from ingestion_service.domain import BlockType, DocumentUnit, ExtractedBlock


_TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".log", ".yaml", ".yml", ".xml"}


class TextReader:
    def supports(self, path: Path, content_type: str) -> bool:
        return path.suffix.lower() in _TEXT_EXTENSIONS or content_type.startswith("text/")

    def units(self, path: Path) -> Iterator[DocumentUnit]:
        text = path.read_text(encoding="utf-8", errors="replace")
        yield DocumentUnit(
            number=1,
            label=path.name,
            blocks=[ExtractedBlock(block_type=BlockType.TEXT, text=text)],
        )


class HTMLReader:
    def supports(self, path: Path, content_type: str) -> bool:
        return path.suffix.lower() in {".html", ".htm"} or content_type == "text/html"

    def units(self, path: Path) -> Iterator[DocumentUnit]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
        for element in soup(["script", "style", "noscript"]):
            element.decompose()
        text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
        yield DocumentUnit(
            number=1,
            label=path.name,
            blocks=[ExtractedBlock(block_type=BlockType.TEXT, text=text)],
        )


class CSVReader:
    def supports(self, path: Path, content_type: str) -> bool:
        return path.suffix.lower() in {".csv", ".tsv"} or content_type in {
            "text/csv",
            "text/tab-separated-values",
        }

    def units(self, path: Path) -> Iterator[DocumentUnit]:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=delimiter))
        text = "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)
        yield DocumentUnit(
            number=1,
            label=path.name,
            blocks=[ExtractedBlock(block_type=BlockType.TABLE, text=text)],
        )


class JSONReader:
    def supports(self, path: Path, content_type: str) -> bool:
        return path.suffix.lower() in {".json", ".jsonl"} or content_type == "application/json"

    def units(self, path: Path) -> Iterator[DocumentUnit]:
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() == ".jsonl":
            values = [json.loads(line) for line in raw.splitlines() if line.strip()]
        else:
            values = json.loads(raw)
        pretty = json.dumps(values, ensure_ascii=False, indent=2)
        yield DocumentUnit(
            number=1,
            label=path.name,
            blocks=[ExtractedBlock(block_type=BlockType.TEXT, text=pretty)],
        )
