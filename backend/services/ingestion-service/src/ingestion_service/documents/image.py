from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from PIL import Image

from ingestion_service.domain import Asset, BlockType, DocumentUnit, ExtractedBlock

from .ocr import OCREngine


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


class ImageReader:
    def __init__(self, ocr: OCREngine | None) -> None:
        self._ocr = ocr

    def supports(self, path: Path, content_type: str) -> bool:
        return path.suffix.lower() in _IMAGE_EXTENSIONS or content_type.startswith("image/")

    def units(self, path: Path) -> Iterator[DocumentUnit]:
        data = path.read_bytes()
        with Image.open(path) as image:
            width, height = image.size
            image_format = (image.format or path.suffix.lstrip(".") or "png").lower()
            content_type = Image.MIME.get(image.format or "", f"image/{image_format}")
            ocr_text = self._ocr.image_text(image) if self._ocr else ""
        fallback = ocr_text or f"Image document {path.name} ({width}x{height})."
        yield DocumentUnit(
            number=1,
            label=path.name,
            blocks=[
                ExtractedBlock(
                    block_type=BlockType.IMAGE,
                    text=fallback,
                    metadata={"ocr": bool(ocr_text)},
                )
            ],
            assets=[
                Asset(
                    data=data,
                    extension=image_format,
                    content_type=content_type,
                    width=width,
                    height=height,
                    ocr_text=ocr_text,
                )
            ],
        )

