"""
tests/test_span_reader.py
=========================
Verifies read_spans() on real synthetic PyMuPDF pages: it extracts text with the
right fields, detects bold, preserves grouping, and skips image blocks.
"""

import fitz  # PyMuPDF

from src.ingestion.extraction.span_reader import read_spans, Span


def test_reads_text_spans_with_fields():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Hello world", fontsize=12, fontname="helv")

    spans = read_spans(page)

    assert len(spans) >= 1
    joined = "".join(s.text for s in spans)
    assert "Hello world" in joined
    first = spans[0]
    assert isinstance(first, Span)
    assert first.size == 12.0
    assert first.font != ""
    assert len(first.bbox) == 4


def test_detects_bold():
    doc = fitz.open()
    page = doc.new_page()
    # "hebo" == Helvetica-Bold in PyMuPDF's base-14 fonts.
    page.insert_text((72, 100), "Bold heading", fontsize=14, fontname="hebo")

    spans = read_spans(page)
    assert any(s.bold for s in spans)


def test_skips_image_blocks():
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 400, 400))
    pix.set_rect(pix.irect, (200, 200, 200))
    page.insert_image(page.rect, pixmap=pix)  # image only, no text

    spans = read_spans(page)
    assert spans == []


def test_empty_page_returns_empty_list():
    doc = fitz.open()
    page = doc.new_page()
    assert read_spans(page) == []


def test_preserves_line_grouping():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Line one", fontsize=12)
    page.insert_text((72, 130), "Line two", fontsize=12)

    spans = read_spans(page)
    # two separate insert_text calls -> at least two distinct line groups
    line_keys = {(s.block_no, s.line_no) for s in spans}
    assert len(line_keys) >= 2