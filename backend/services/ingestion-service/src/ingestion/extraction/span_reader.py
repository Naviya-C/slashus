"""
extraction/span_reader.py
=========================

PURPOSE
-------
Turn ONE digital PDF page into a flat list of `Span` objects.

A span is PyMuPDF's atomic unit of text: a run of characters that all share the
same font, size, and style. It is the ONLY level that carries the font name --
and the font name is exactly what the next stage (span_converter) needs to
decide "is this legacy Sinhala that piliwela must convert, or Latin to leave
alone". So this module's whole job is to surface spans cleanly, with the fields
downstream stages depend on:

    text  -> the characters        (still RAW here: legacy bytes are NOT yet converted)
    font  -> the font family name  (span_converter uses this to route to piliwela)
    size  -> font size             (layout/sections uses this to detect headings)
    bold  -> is it bold            (layout/sections uses this to detect headings)
    bbox  -> position on the page  (reading order, tables, image association)

WHAT THIS MODULE DOES (and does not do)
---------------------------------------
- PURE FUNCTION over a `pymupdf.Page`, exactly like the detector. It only READS.
  It does NOT convert fonts, build lines/paragraphs, detect headings, or chunk.
  Those are later stages. Keeping it read-only makes it trivial to unit-test.
- It walks blocks -> lines -> spans and flattens to a list, but preserves the
  `block_no` and `line_no` of each span. That grouping is what lets the next
  stage reassemble a line after converting its spans, and lets the layout stage
  group lines into paragraphs. Nothing about position is lost.
- It SKIPS image blocks (PyMuPDF block type 1). Images are not text; they are
  handled by the image side-channel (image_extractor + caption_images), not here.

WHY RAW TEXT (not converted) COMES OUT OF HERE
----------------------------------------------
Conversion is deliberately the NEXT step, not this one. This module's output is
the raw span list -- legacy Sinhala bytes are still legacy at this point. The
separation keeps reading and converting independently testable: this file proves
"we extracted the right spans with the right fonts"; span_converter proves
"we converted the right spans and left English alone".
"""

from __future__ import annotations

from dataclasses import dataclass


# PyMuPDF span "flags" is a bitfield; bit 4 (value 16) marks bold.
_BOLD_FLAG = 1 << 4

# PyMuPDF block "type": 0 == text block, 1 == image block. We read text only.
_TEXT_BLOCK = 0


@dataclass
class Span:
    """One run of same-styled text, plus where it sits.

    `block_no` / `line_no` are kept so the next stage can regroup spans back
    into their original line (for reassembly) and block (for paragraphs).
    The list order of spans within a line is their left-to-right reading order.
    """

    text: str
    font: str
    size: float
    bold: bool
    bbox: tuple[float, float, float, float]
    block_no: int
    line_no: int


def _is_bold(span: dict) -> bool:
    """True if the span is bold.

    Primary signal is the PyMuPDF flags bit; some fonts don't set it, so we also
    fall back to the font name (e.g. 'Helvetica-Bold', 'FMAbhaya-Bold').
    """
    if span.get("flags", 0) & _BOLD_FLAG:
        return True
    return "bold" in span.get("font", "").lower()


def read_spans(page) -> list[Span]:
    """Read a PyMuPDF page into a flat, reading-order list of Span objects.

    Pure function: give it a `pymupdf.Page`, get back its text spans. Image blocks
    are skipped. Text is returned RAW (not yet font-converted).

    Args:
        page: a PyMuPDF `pymupdf.Page` (caller owns opening/closing the PDF).

    Returns:
        list[Span] in reading order. Empty list for a page with no text.
    """
    spans: list[Span] = []
    data = page.get_text("dict")

    for block_no, block in enumerate(data["blocks"]):
        if block.get("type") != _TEXT_BLOCK:  # skip images; they go elsewhere
            continue
        for line_no, line in enumerate(block["lines"]):
            for raw in line["spans"]:
                spans.append(
                    Span(
                        text = raw["text"],
                        font = raw.get("font", ""),
                        size = round(float(raw.get("size", 0.0)), 2),
                        bold = _is_bold(raw),
                        bbox = tuple(raw["bbox"]),
                        block_no = block_no,
                        line_no = line_no,
                    )
                )

    return spans