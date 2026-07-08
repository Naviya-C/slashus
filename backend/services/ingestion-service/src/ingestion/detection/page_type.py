"""
detection/page_type.py
=======================

PURPOSE
-------
This module answers ONE question about a single PDF page:

    "Does this page have usable text, or is it a picture of text?"

That answer is the ONLY real branch in the whole ingestion pipeline. Everything
downstream is language-blind and format-blind, but it must know which of two
extraction routes a page takes:

    DIGITAL  -> the page has a real text layer
                -> route to PyMuPDF span extraction + piliwela conversion
    SCANNED  -> the page is a full-page raster image with no text layer
                -> route to OCR (sin+eng); piliwela is NOT used (OCR emits Unicode)
    EMPTY    -> no usable text and no page-sized image (blank / divider page)
                -> skip; there is nothing to extract

WHAT THIS MODULE DOES (and does not do)
---------------------------------------
- It is a PURE FUNCTION over a single `pymupdf.Page`. It does NOT open the PDF,
  loop pages, call piliwela, run OCR, or build chunks. Those belong to the
  orchestrator (pipeline/ingest.py) and the extraction modules.
- Keeping it pure is deliberate: it makes the detector trivially unit-testable
  with synthetic pages, and it has ZERO dependency on any port, adapter, or the
  chunk contract.
  
HOW THE DECISION IS MADE
------------------------
Two cheap signals are read off the page:

    1. char_count  -> length of the extractable text  (0 on a real scan)
    2. coverage    -> largest raster image area / page area  (~1.0 on a scan)

The ORDER matters. Text is checked FIRST:

    if char_count  >= text_threshold     -> DIGITAL
    elif coverage  >= coverage_threshold -> SCANNED
    else                                 -> EMPTY

Checking text first is what makes the tricky cases land correctly:
    * Illustrated digital page (diagram + real text): high coverage AND high
      text -> text wins -> DIGITAL. The image goes down the image side-channel,
      not to OCR.
    * Already-OCR'd scan (image + baked-in invisible text layer): both high ->
      DIGITAL, so we reuse the existing text instead of re-OCR'ing it.
    * Legacy-Sinhala page: FM-font bytes ARE a text layer -> high char_count ->
      DIGITAL -> sent to piliwela. The detector never needs to know the language.

TUNING
------
The two thresholds are injected by the caller (from config.py), never hardcoded
at the call site, because they WILL be tuned against a real corpus:
    * text_threshold     ~50-100 chars : how much text counts as "a real layer".
                                          Raise it if scans leak a few stray chars.
    * coverage_threshold ~0.5-0.8       : how much of the page an image must fill
                                          to read as a scan. Lower it if your scans
                                          have wide margins.

The function returns the raw signals alongside the decision so you can watch the
actual numbers while tuning thresholds on your own PDFs, instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..config import load_env

globalConfig = load_env()

DEFAULT_TEXT_THRESHOLD: int = globalConfig["DEFAULT_TEXT_THRESHOLD"]  
DEFAULT_COVERAGE_THRESHOLD: float = globalConfig["DEFAULT_COVERAGE_THRESHOLD"]


class PageType(str, Enum):
    """The routing decision for a page. The orchestrator branches on this.

    Subclassing `str` makes it JSON-serialisable and log-friendly while still
    being a real enum (so comparisons are type-checked, not stringly-typed).
    """

    DIGITAL = "digital"   # has a text layer -> spans + piliwela
    SCANNED = "scanned"   # image of text    -> OCR (sin+eng), no piliwela
    EMPTY = "empty"       # nothing usable   -> skip


@dataclass(frozen=True)
class PageTypeResult:
    """The decision plus the raw signals it was made from.

    `char_count` and `coverage` are returned on purpose: they are what you look
    at when calibrating the thresholds against real documents.
    """

    decision: PageType
    char_count: int
    coverage: float


def _largest_image_coverage(page) -> float:
    """Return (area of the largest raster image on the page) / (page area).

    Reads image blocks (type == 1) from the PyMuPDF text dict and takes the
    single largest one, because a scan is one page-sized image. Summing all
    images would over-count on collage-style pages; the max is the honest
    signal for "is there a page-filling scan here".
    """
    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return 0.0

    largest = 0.0
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") == 1:  # 1 == image block
            x0, y0, x1, y1 = block["bbox"]
            largest = max(largest, abs((x1 - x0) * (y1 - y0)))

    return largest / page_area


def classify_page(
    page,
    *,
    text_threshold = DEFAULT_TEXT_THRESHOLD,
    coverage_threshold = DEFAULT_COVERAGE_THRESHOLD,
) -> PageTypeResult:
    """Classify a single PDF page as DIGITAL, SCANNED, or EMPTY.

    This is the pipeline's one branch. Pure function: give it a `fitz.Page`
    and it returns a decision plus the signals behind it. It does not mutate
    the page or touch anything else.

    Args:
        page: a PyMuPDF `fitz.Page` (the caller owns opening/closing the PDF).
        text_threshold: min chars to count as a usable text layer (from config).
        coverage_threshold: min image-area fraction to count as a scan (from config).

    Returns:
        PageTypeResult(decision, char_count, coverage).
    """
    char_count = len(page.get_text("text").strip())
    coverage = _largest_image_coverage(page)

    if char_count >= text_threshold:
        decision = PageType.DIGITAL
    elif coverage >= coverage_threshold:
        decision = PageType.SCANNED
    else:
        decision = PageType.EMPTY

    return PageTypeResult(decision=decision, char_count=char_count, coverage=coverage)