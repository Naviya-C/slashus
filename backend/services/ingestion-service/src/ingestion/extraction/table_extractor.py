"""
extraction/table_extractor.py
=============================

PURPOSE
-------
Turn each table on a page into ONE atomic chunk (markdown -> content; an LLM
one-line summary -> what you embed, added by enrichment/summarize_tables.py).

DETECTION: pdfplumber.   TEXT: PyMuPDF + piliwela.
-------------------------------------------------
Real Sri Lankan PDFs detect better with pdfplumber,
Because I've tested using PyMuPDF but table detection was very poor.
Therefore:
    I decieded to use pdfplumber finds the tables and their cell bounding boxes. 
    But pdfplumber's extract_table() returns,
    plain strings -- for a legacy-font cell that is raw FM bytes with no font, so
    piliwela cannot run and you would embed garbage.

So we split the job:
    pdfplumber  -> detect table structure (each cell's bbox)
    PyMuPDF     -> read the spans clipped to that bbox (keeps the font)
    piliwela    -> convert each span
    
This keeps cell text font-aware while using the better detector. pdfplumber and
PyMuPDF share the same top-left coordinate system, so a cell bbox clips directly
(verified). Rotated pages / non-zero mediabox origins are a later concern.

INPUTS
------
Both a fitz page and the matching pdfplumber page for the SAME page number. The
orchestrator opens both documents once (fitz.open + pdfplumber.open) and walks
them in parallel, so this stays cheap per call.

WHAT IT DOES NOT DO
-------------------
No embedding, no LLM summary, no chunk metadata. Rectangular grids only
(merged/colspan headers are a later concern).
"""

from __future__ import annotations

from dataclasses import dataclass

import fitz  
import piliwela

@dataclass
class Table:
    markdown: str
    n_rows: int
    n_cols: int
    bbox: tuple[float, float, float, float]


def _cell_text(fitz_page, bbox, converter) -> str:
    """Read one cell's text by clipping span extraction to its bbox, converting
    each span (keeps font -> piliwela works). Empty cell -> ''."""
    if bbox is None:
        return ""
    clip = fitz.Rect(bbox) & fitz_page.rect  
    if clip.is_empty:
        return ""
    data = fitz_page.get_text("dict", clip=clip)
    parts: list[str] = []
    for block in data["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"]
                if text.strip():
                    text = converter.convert(text, span.get("font", ""))
                parts.append(text)
    return " ".join(t.strip() for t in parts if t.strip())


def _to_markdown(grid: list[list[str]]) -> str:
    """Render a rectangular grid as a GitHub-style markdown table (row 0 = header)."""
    if not grid:
        return ""

    def row(cells: list[str]) -> str:
        return "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |"

    n_cols = max(len(r) for r in grid)
    grid = [r + [""] * (n_cols - len(r)) for r in grid]
    header = row(grid[0])
    sep = "| " + " | ".join(["---"] * n_cols) + " |"
    body = "\n".join(row(r) for r in grid[1:])
    return "\n".join([header, sep, body]) if body else "\n".join([header, sep])


def extract_tables(fitz_page, plumber_page, converter) -> list[Table]:
    """Detect tables with pdfplumber; fill cell text with PyMuPDF + piliwela.

    Args:
        fitz_page: PyMuPDF `fitz.Page` (for font-aware cell text).
        plumber_page: the matching pdfplumber page (for detection).
        converter: a FontConverter (real piliwela, or a fake).

    Returns:
        list[Table] in the order pdfplumber reports them.
    """
    tables: list[Table] = []

    for t in plumber_page.find_tables():
        boxes = [c for c in t.cells if c]
        if not boxes:
            continue

        # place cells by their coordinates (ordering-agnostic)
        tops = sorted({round(b[1], 1) for b in boxes})
        lefts = sorted({round(b[0], 1) for b in boxes})
        grid: list[list[str]] = [["" for _ in lefts] for _ in tops]
        for b in boxes:
            r = tops.index(round(b[1], 1))
            c = lefts.index(round(b[0], 1))
            grid[r][c] = _cell_text(fitz_page, b, converter)

        tables.append(
            Table(
                markdown=_to_markdown(grid),
                n_rows=len(grid),
                n_cols=(len(grid[0]) if grid else 0),
                bbox=tuple(t.bbox),
            )
        )

    return tables