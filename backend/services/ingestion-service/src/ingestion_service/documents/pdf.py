from __future__ import annotations

import io
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image

from ingestion_service.config import Settings
from ingestion_service.domain import Asset, BlockType, DocumentUnit, ExtractedBlock

from .ocr import OCREngine
from .piliwela_adapter import PiliwelaConverter


@dataclass(frozen=True)
class DocumentStyleProfile:
    body_size: float


class PDFReader:
    def __init__(
        self,
        *,
        settings: Settings,
        ocr: OCREngine | None,
        converter: PiliwelaConverter,
    ) -> None:
        self._cfg = settings
        self._ocr = ocr
        self._converter = converter

    def supports(self, path: Path, content_type: str) -> bool:
        return path.suffix.lower() == ".pdf" or content_type == "application/pdf"

    def units(self, path: Path) -> Iterator[DocumentUnit]:
        with pymupdf.open(path) as document:
            if document.page_count > self._cfg.max_document_units:
                raise ValueError(f"document has {document.page_count} pages; limit exceeded")
            profile = self._style_profile(document)
            section_stack: list[str] = []
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                table_blocks, table_boxes = self._table_blocks(page, section_stack)
                blocks, section_stack = self._text_blocks(
                    page, section_stack, table_boxes, profile
                )
                if sum(len(block.text.strip()) for block in blocks) < self._cfg.ocr_min_text_characters:
                    blocks = self._ocr_blocks(page, section_stack) or blocks
                assets = self._images(page)
                yield DocumentUnit(
                    number=page_index + 1,
                    label=f"page {page_index + 1}",
                    blocks=[*blocks, *table_blocks],
                    assets=assets,
                    metadata={"format": "pdf"},
                )
                page = None

    def _text_blocks(
        self,
        page: pymupdf.Page,
        section_stack: list[str],
        excluded_boxes: list[tuple[float, float, float, float]],
        profile: DocumentStyleProfile,
    ) -> tuple[list[ExtractedBlock], list[str]]:
        raw = page.get_text("dict", sort=True)
        spans: list[dict[str, Any]] = []
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                line_parts: list[str] = []
                line_sizes: list[float] = []
                flags = 0
                bbox = tuple(line.get("bbox") or (0, 0, 0, 0))
                for span in line.get("spans", []):
                    text = str(span.get("text") or "")
                    if text.strip():
                        text = self._converter.convert(text, str(span.get("font") or ""))
                    line_parts.append(text)
                    size = float(span.get("size") or 0)
                    if text.strip():
                        line_sizes.append(size)
                    flags |= int(span.get("flags") or 0)
                text = "".join(line_parts).strip()
                if text and not _center_in_any(bbox, excluded_boxes):
                    spans.append(
                        {
                            "text": text,
                            "size": max(line_sizes, default=0),
                            "flags": flags,
                            "bbox": bbox,
                        }
                    )

        if not spans:
            return [], section_stack
        result: list[ExtractedBlock] = []
        current_section = list(section_stack)
        for item in spans:
            text = item["text"]
            is_bold = bool(item["flags"] & 16)
            level = _heading_level(
                text=text,
                size=item["size"],
                bold=is_bold,
                body_size=profile.body_size,
                max_characters=self._cfg.heading_max_characters,
                h1_ratio=self._cfg.heading_h1_ratio,
                h2_ratio=self._cfg.heading_h2_ratio,
                h3_ratio=self._cfg.heading_h3_ratio,
            )
            if level is not None:
                # Never create a hierarchy with missing parents. A document that
                # starts with an H2-sized line treats it as its current top level.
                level = min(level, len(current_section) + 1)
                current_section = [*current_section[: level - 1], text]
                result.append(
                    ExtractedBlock(
                        block_type=BlockType.HEADING,
                        text=text,
                        section_path=list(current_section),
                        bbox=item["bbox"],
                        metadata={
                            "heading_level": level,
                            "font_size": item["size"],
                            "body_font_size": profile.body_size,
                        },
                    )
                )
            else:
                result.append(
                    ExtractedBlock(
                        block_type=BlockType.PARAGRAPH,
                        text=text,
                        section_path=list(current_section),
                        bbox=item["bbox"],
                    )
                )
        return result, current_section

    @staticmethod
    def _style_profile(document: pymupdf.Document) -> DocumentStyleProfile:
        """Find the document body font using character-weighted frequency."""
        weights: dict[float, int] = {}
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            raw = page.get_text("dict", sort=False)
            for block in raw.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = str(span.get("text") or "").strip()
                        size = round(float(span.get("size") or 0), 1)
                        if text and size > 0:
                            weights[size] = weights.get(size, 0) + len(text)
            page = None
        body_size = max(weights, key=weights.get) if weights else 10.0
        return DocumentStyleProfile(body_size=body_size)

    def _ocr_blocks(
        self, page: pymupdf.Page, section_stack: list[str]
    ) -> list[ExtractedBlock]:
        if self._ocr is None:
            return []
        text = self._ocr.pdf_page_text(page)
        if not text:
            return []
        return [
            ExtractedBlock(
                block_type=BlockType.TEXT,
                text=text,
                section_path=list(section_stack),
                metadata={"ocr": True},
            )
        ]

    def _table_blocks(
        self, page: pymupdf.Page, section_stack: list[str]
    ) -> tuple[list[ExtractedBlock], list[tuple[float, float, float, float]]]:
        try:
            finder = page.find_tables()
        except Exception:
            return [], []
        blocks: list[ExtractedBlock] = []
        boxes: list[tuple[float, float, float, float]] = []
        seen: set[str] = set()
        for table in finder.tables:
            try:
                rows = table.extract()
            except Exception:
                continue
            normalized = [
                [str(cell or "").strip() for cell in row]
                for row in rows
                if any(str(cell or "").strip() for cell in row)
            ]
            if not normalized:
                continue
            markdown = _markdown_table(normalized)
            if markdown in seen:
                continue
            seen.add(markdown)
            blocks.append(
                ExtractedBlock(
                    block_type=BlockType.TABLE,
                    text=markdown,
                    section_path=list(section_stack),
                    bbox=tuple(table.bbox),
                    metadata={"rows": len(normalized), "columns": max(map(len, normalized))},
                )
            )
            boxes.append(tuple(table.bbox))
        return blocks, boxes

    def _images(self, page: pymupdf.Page) -> list[Asset]:
        if not self._cfg.extract_images or self._cfg.max_images_per_unit == 0:
            return []
        assets: list[Asset] = []
        seen: set[int] = set()
        page_area = max(float(page.rect.width * page.rect.height), 1.0)
        for image_info in page.get_images(full=True):
            xref = int(image_info[0])
            if xref in seen:
                continue
            seen.add(xref)
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            rect = max(rects, key=lambda candidate: abs(candidate))
            area_ratio = abs(rect) / page_area
            extracted = page.parent.extract_image(xref)
            data = extracted.get("image")
            if not data:
                continue
            width = int(extracted.get("width") or 0)
            height = int(extracted.get("height") or 0)
            if width < self._cfg.min_image_width or height < self._cfg.min_image_height:
                continue
            if area_ratio < self._cfg.min_image_area_ratio:
                continue
            extension = str(extracted.get("ext") or "png").lower()
            content_type = Image.MIME.get(extension.upper(), f"image/{extension}")
            ocr_text = ""
            if self._ocr is not None:
                try:
                    ocr_text = self._ocr.bytes_text(data)
                except Exception:
                    ocr_text = ""
            assets.append(
                Asset(
                    data=data,
                    extension=extension,
                    content_type=content_type,
                    width=width,
                    height=height,
                    bbox=tuple(rect),
                    ocr_text=ocr_text,
                )
            )
            if len(assets) >= self._cfg.max_images_per_unit:
                break
        return assets


def _markdown_table(rows: list[list[str]]) -> str:
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]

    def render(row: list[str]) -> str:
        return "| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |"

    return "\n".join([render(padded[0]), render(["---"] * width), *map(render, padded[1:])])


def _center_in_any(
    bbox: tuple[float, float, float, float],
    boxes: list[tuple[float, float, float, float]],
) -> bool:
    x0, y0, x1, y1 = bbox
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2
    return any(
        left <= center_x <= right and top <= center_y <= bottom
        for left, top, right, bottom in boxes
    )


def _heading_level(
    *,
    text: str,
    size: float,
    bold: bool,
    body_size: float,
    max_characters: int,
    h1_ratio: float,
    h2_ratio: float,
    h3_ratio: float,
) -> int | None:
    normalized = " ".join(text.split())
    if not normalized or len(normalized) > max_characters:
        return None
    if len(normalized.split()) > 24:
        return None
    if normalized.isdigit():
        return None
    # Ordinary prose ending in sentence punctuation should not become a title.
    if normalized.endswith((".", "?", "!", "。", "？", "！")):
        return None
    ratio = size / max(body_size, 0.1)
    if ratio >= h1_ratio:
        return 1
    if ratio >= h2_ratio:
        return 2
    if ratio >= h3_ratio and bold:
        return 3
    return None
