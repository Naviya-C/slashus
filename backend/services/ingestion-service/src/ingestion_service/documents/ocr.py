from __future__ import annotations

import io

import pymupdf
import pytesseract
from PIL import Image, ImageOps


class OCREngine:
    def __init__(self, *, languages: str, dpi: int, timeout_seconds: int) -> None:
        self._languages = languages
        self._dpi = dpi
        self._timeout = timeout_seconds

    def image_text(self, image: Image.Image) -> str:
        normalized = ImageOps.exif_transpose(image).convert("L")
        normalized = ImageOps.autocontrast(normalized)
        return pytesseract.image_to_string(
            normalized,
            lang=self._languages,
            config="--oem 1 --psm 6",
            timeout=self._timeout,
        ).strip()

    def bytes_text(self, data: bytes) -> str:
        with Image.open(io.BytesIO(data)) as image:
            return self.image_text(image)

    def pdf_page_text(self, page: pymupdf.Page) -> str:
        scale = self._dpi / 72.0
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
            return self.image_text(image)

