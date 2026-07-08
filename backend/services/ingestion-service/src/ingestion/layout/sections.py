"""
layout/sections.py
==================

PURPOSE
-------
Turn the flat list of clean Lines into a SINGLE running TITLE per position.

We deliberately DO NOT build nested H1>H2>H3 paths. In legacy Sinhala
textbooks the only reliable structural signal is the big lesson title; trying
to detect and nest sub-headings (author lists, bold key-terms, exercise
labels) produces far more noise than value. So this module extracts ONE level
of heading -- the title -- and every chunk simply carries the title of the
lesson it sits in. Flat, robust, embeddable.

HOW A TITLE IS DETECTED (font size leads)
-----------------------------------------
`_heading_level(text, size, all_sizes)` ranks a line against the page's body
(median) size:

        short line (<=30 chars):  >=1.6x ->1   >=1.15x ->2   >=1.05x ->3
        long  line (>30  chars):  >=1.6x ->1   >=1.30x ->2   >=1.20x ->3

Only level-1 lines (>=1.6x body) are treated as TITLES. Levels 2/3 are ignored
for sectioning -- keeping them out is exactly what removes the mess. A few hard
gates reject non-titles that happen to be big: number-only lines (page numbers),
single glyphs (chart cells), and lines that close a sentence/quote.

SECTION ASSIGNMENT (by position, not reading order)
---------------------------------------------------
`SectionIndex` holds the titles found on a page, sorted top-to-bottom. Any item
at y_top gets the LAST title at or above it (or the title carried in from the
previous page, so a lesson title spans its whole run of pages). Text blocks,
tables and images all use the same `path_for(y_top)` lookup, so everything under
a title is titled -- including content that precedes the title in PyMuPDF's
reading order.

WHAT IT DOES NOT DO
-------------------
No sub-heading nesting, no paragraph merging (that's blocks.py), no chunking.
Pure functions over Lines; no PDF, no ports, no LLM. Single-column assumption.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import median

from src.ingestion.extraction.span_converter import Line


# ------------------------- tunable thresholds ------------------------------- #
TITLE_LEVEL = 1            # only level-1 headings (>=1.6x body) count as titles
MAX_TITLE_CHARS = 120      # a title never runs longer than this
TITLE_MERGE_GAP = 1.8      # merge a 2nd title line if within this * its height below
_NUMBER_RE = re.compile(r"^[\d\s.,:/–-]+$")   # page numbers / rule lines -> not a title


@dataclass
class LineInfo:
    """A line plus the derived features used to classify it, and the results."""

    text: str
    size: float
    bold: bool
    word_count: int
    bbox: tuple[float, float, float, float]
    block_no: int = 0
    line_no: int = 0
    gap_above: float = 0.0
    is_heading: bool = False          # True == this line is a TITLE (level 1)
    level: int = 0                    # 1 for a title, 0 otherwise
    section_path: list[str] = field(default_factory=list)


# ----------------------------- helpers -------------------------------------- #
def _char_weighted_median(pairs: list[tuple[float, int]]) -> float:
    """Median value weighted by character count (so a long 12pt run outweighs a
    stray 30pt character). pairs = [(size, char_count), ...]."""
    items = sorted((v, w) for v, w in pairs if w > 0)
    total = sum(w for _, w in items)
    if total == 0:
        return 0.0
    half = total / 2
    cum = 0
    for v, w in items:
        cum += w
        if cum >= half:
            return v
    return items[-1][0]


def _line_info(line: Line) -> LineInfo:
    """Derive per-line features from its spans."""
    spans = line.spans
    size = _char_weighted_median([(s.size, len(s.text)) for s in spans])

    total_chars = sum(len(s.text) for s in spans) or 1
    bold_chars = sum(len(s.text) for s in spans if s.bold)
    bold = (bold_chars / total_chars) >= 0.60

    x0 = min(s.bbox[0] for s in spans)
    y0 = min(s.bbox[1] for s in spans)
    x1 = max(s.bbox[2] for s in spans)
    y1 = max(s.bbox[3] for s in spans)

    return LineInfo(
        text=line.text,
        size=round(size, 2),
        bold=bold,
        word_count=len(line.text.split()),
        bbox=(x0, y0, x1, y1),
        block_no=line.block_no,
        line_no=line.line_no,
    )


def body_font_size(infos: list[LineInfo]) -> float:
    """Char-weighted median size across all lines -> the body text size."""
    return _char_weighted_median([(info.size, len(info.text)) for info in infos])


def median_line_height(infos: list[LineInfo]) -> float:
    """Median line height; used by blocks.py as the paragraph-gap yardstick."""
    heights = [info.bbox[3] - info.bbox[1] for info in infos if info.bbox[3] > info.bbox[1]]
    return median(heights) if heights else 1.0


def _heading_level(text: str, font_size: float, all_sizes: list[float]) -> int | None:
    """Rank a line by how much bigger than body it is. Font size leads.

    Short lines are allowed to qualify at smaller ratios than long lines (a long
    line has to be *much* bigger to count, which keeps big body lines out).
    Returns 1/2/3 or None. Only level 1 is used as a title (see _is_title).
    """
    if not all_sizes:
        return None
    body = sorted(all_sizes)[len(all_sizes) // 2]
    text = text.strip()
    if len(text) <= 30:
        if font_size >= body * 1.6:
            return 1
        elif font_size >= body * 1.15:
            return 2
        elif font_size >= body * 1.05:
            return 3
    else:
        if font_size >= body * 1.6:
            return 1
        elif font_size >= body * 1.3:
            return 2
        elif font_size >= body * 1.2:
            return 3
    return None


def _is_title(info: LineInfo, all_sizes: list[float]) -> bool:
    """A line is a TITLE iff it is level-1 by size AND passes non-title gates."""
    text = info.text.strip()
    if not text or len(text) > MAX_TITLE_CHARS:
        return False
    if _NUMBER_RE.match(text):                 # page numbers / rules
        return False
    if len(text.replace(" ", "")) < 2:         # single-glyph chart cells
        return False
    if text[-1] in {".", ",", ";", ":", "!", "?", "\u201d", "\""}:
        return False
    level = _heading_level(text, info.size, all_sizes)
    return level is not None and level <= TITLE_LEVEL


class SectionIndex:
    """Assigns a FLAT title to any item BY VERTICAL POSITION, not reading order.

    Titles on the page are sorted top-to-bottom; an item at y_top gets the last
    title at or above it, else the title carried in from the previous page (so a
    lesson title spans its whole page run). Text blocks, tables and images share
    this one lookup -- everything under a title is titled.

    The "carry" between pages is just the last title string (no stack of parents),
    which is the whole point: one level, no nesting, no mess.
    """

    _TOL = 2.0  # a title covers items whose top is at/below it (small slack)

    def __init__(self, infos: list[LineInfo], carried_title: str | None = None):
        self._carried = carried_title
        self._events: list[tuple[float, str]] = [
            (i.bbox[1], i.text.strip()) for i in infos if i.is_heading
        ]
        self._events.sort(key=lambda e: e[0])

    def path_for(self, y_top: float) -> list[str]:
        """Return the title for an item at y_top as a 0- or 1-element list.

        A list keeps the Chunk.section_path type stable (join -> the title, or ""
        when there is no title in scope).
        """
        title = self._carried
        for hy, t in self._events:            # sorted by y ascending
            if hy <= y_top + self._TOL:
                title = t
            else:
                break
        return [title] if title else []

    @property
    def final_stack(self) -> str | None:
        """Last title on the page (or the carried one) to thread into the next page."""
        return self._events[-1][1] if self._events else self._carried


def _merge_split_titles(infos: list[LineInfo]) -> None:
    """Some lesson titles wrap onto two lines (same big size, stacked). Merge the
    second line's text into the first and demote the second, so the title reads as
    one string ("... v.lH iy" + "l¾u ldrl jdlH")."""
    titles = [i for i in infos if i.is_heading]
    titles.sort(key=lambda i: i.bbox[1])
    for a, b in zip(titles, titles[1:]):
        if not b.is_heading:
            continue
        same_size = abs(a.size - b.size) <= 0.6
        close = 0 <= (b.bbox[1] - a.bbox[3]) <= (b.bbox[3] - b.bbox[1]) * TITLE_MERGE_GAP
        if same_size and close:
            a.text = f"{a.text.strip()} {b.text.strip()}"
            b.is_heading = False
            b.level = 0


def build_sections(
    lines: list[Line],
    carried_title: str | None = None,
) -> tuple[list[LineInfo], SectionIndex]:
    """Classify lines into TITLE / body and build a flat, y-position SectionIndex.

    `carried_title` is the last title from the previous page (a plain string or
    None) so a lesson title spans page breaks. Returns (infos, index); the caller
    assigns section via index.path_for(y) for text blocks, tables and images, and
    threads index.final_stack into the next page.
    """
    infos = [_line_info(line) for line in lines if line.text.strip()]
    if not infos:
        return [], SectionIndex([], carried_title)

    all_sizes = [i.size for i in infos]
    for info in infos:
        info.is_heading = _is_title(info, all_sizes)
        info.level = TITLE_LEVEL if info.is_heading else 0

    _merge_split_titles(infos)
    return infos, SectionIndex(infos, carried_title)