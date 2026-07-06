"""
tests/test_detection.py
========================
Verifies classify_page() on the three real cases: a digital text page, a
scanned (full-page image) page, and a near-empty divider page. Uses synthetic
PyMuPDF pages so the test needs no fixture files and runs in milliseconds.
"""

import fitz  

from src.ingestion.detection.page_type import classify_page, PageType


def _digital_page(doc):
    p = doc.new_page()
    p.insert_text((72, 100),
                  "This is a digital page with a real text layer.\n"
                  "PyMuPDF can extract every character directly.", fontsize=12)
    return p


def _scanned_page(doc):
    p = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 600, 800))
    pix.set_rect(pix.irect, (230, 230, 230))  # a page-filling image
    p.insert_image(p.rect, pixmap=pix)        # no text inserted
    return p


def _empty_page(doc):
    p = doc.new_page()
    p.insert_text((300, 780), "", fontsize=10)  
    return p


def test_digital_page_is_digital():
    doc = fitz.open()
    result = classify_page(_digital_page(doc))
    assert result.decision is PageType.DIGITAL
    assert result.char_count >= 50


def test_scanned_page_is_scanned():
    doc = fitz.open()
    result = classify_page(_scanned_page(doc))
    assert result.decision is PageType.SCANNED
    assert result.char_count == 0
    assert result.coverage >= 0.5


def test_empty_page_is_empty():
    doc = fitz.open()
    result = classify_page(_empty_page(doc))
    assert result.decision is PageType.EMPTY


def test_thresholds_are_injectable():
    # With a very high text threshold, even the digital page falls through to EMPTY.
    doc = fitz.open()
    result = classify_page(_digital_page(doc), text_threshold=10_000)
    assert result.decision is PageType.EMPTY