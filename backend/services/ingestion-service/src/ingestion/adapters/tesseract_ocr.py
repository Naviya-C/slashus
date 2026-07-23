"""
adapters/tesseract_ocr.py
=========================

PURPOSE
-------
Real OCREngine via pytesseract, for scanned pages in Sinhala textbooks.

Requires (system + python):
    sudo apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-eng
    pip install pytesseract pillow

DESIGN
------
- Renders the fitz page at 300 DPI grayscale — the sweet spot for Sinhala
  glyph accuracy vs speed; 72 DPI (the default) is unreadable to tesseract.
- lang="sin+eng" so mixed Sinhala/English textbook pages read correctly.
- --psm 6 (assume a uniform block of text) works best for book pages;
  override via `config` for unusual layouts.
- Constructor probes tesseract once, so deps._safe() can fall back to
  "skip scanned pages" when the binary or language packs are missing,
  instead of failing mid-ingest on page 47.
"""

from __future__ import annotations

import io
import logging

import fitz  # PyMuPDF

log = logging.getLogger(__name__)

_RENDER_DPI = 300


class TesseractOCR:
    """OCREngine backed by a local tesseract install (sin+eng)."""

    def __init__(self, lang: str = "sin+eng", config: str = "--psm 6") -> None:
        import pytesseract  # imported here so the adapter is optional
        from PIL import Image

        self._pytesseract = pytesseract
        self._Image = Image
        self._lang = lang
        self._config = config

        # Fail fast at construction, not on page 47 of an ingest.
        available = set(pytesseract.get_languages(config=""))
        missing = [l for l in lang.split("+") if l not in available]
        if missing:
            raise RuntimeError(
                f"tesseract language pack(s) missing: {missing}. "
                f"Install: sudo apt install "
                + " ".join(f"tesseract-ocr-{l}" for l in missing)
            )

    def read(self, page) -> str:
        """Rasterize the page and OCR it. Returns "" when nothing is read."""
        pix = page.get_pixmap(dpi=_RENDER_DPI, colorspace=fitz.csGRAY)
        img = self._Image.open(io.BytesIO(pix.tobytes("png")))
        text = self._pytesseract.image_to_string(
            img, lang=self._lang, config=self._config
        )
        return text.strip()
