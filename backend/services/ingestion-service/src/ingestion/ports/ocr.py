"""
ports/ocr.py
============

PURPOSE
-------
The seam between the pipeline and whatever OCR engine reads scanned pages.
The pipeline calls THIS interface; tesseract (or a cloud OCR later) plugs in
behind it, so swapping engines never touches pipeline code.

THE CONTRACT
------------
    read(page) -> str    OCR a PyMuPDF page, return plain text ("" if nothing)

The engine receives the fitz Page (not raw bytes) so it controls its own
rendering (DPI, grayscale) — rendering choices are an OCR concern, not a
pipeline concern.
"""

from __future__ import annotations

from typing import Protocol


class OCREngine(Protocol):
    def read(self, page) -> str: ...
