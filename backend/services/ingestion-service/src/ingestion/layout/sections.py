"""
layout/sections.py
==================

PURPOSE
-------
Turn the flat list of clean Lines into STRUCTURE: decide which lines are
headings vs body, give headings levels (H1/H2/H3), and hand every line the
section path it lives under (e.g. ["Chapter 3", "Photosynthesis"]).

That section path is what makes chunks meaningful: the chunker never merges
across a heading, and prepends the path as a breadcrumb before embedding.

HOW A HEADING IS DETECTED (multi-signal, not size alone)
--------------------------------------------------------
A single rule ("bigger font = heading") is fragile. We score several signals:

    size   : char-weighted size vs the body median   (bigger -> heading)
    bold   : is the line mostly bold                  (bold   -> heading)
    center : is the line centered in the text column  (centered -> heading)
    width  : is the line much narrower than body      (narrow -> heading)
    gap    : is there extra whitespace above it        (isolated -> heading)

    word count is a HARD GATE, not a score:
        * a long line is NEVER a heading (rejects big-font pull-quotes)
        * this is what lets a short, bold, SAME-SIZE run-in heading still win
          on bold+narrow+isolated, while a long body line never can.

Levels come from ranking the distinct heading sizes: largest -> H1, next -> H2,
capped at 3. Paths come from walking the lines and keeping a heading stack.

WHAT IT DOES NOT DO
-------------------
No paragraph merging (that's blocks.py, which builds on this) and no chunking.
Pure functions over Lines; no PDF, no ports, no LLM. Assumes single-column
layout (multi-column is a later concern).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from src.ingestion.extraction.span_converter import Line


# ------------------------- tunable thresholds ------------------------------- #
SIZE_RATIO_STRONG = 1.15   # >= this * body size -> strong heading signal (+2)
SIZE_RATIO_WEAK = 1.05     # >= this * body size -> weak heading signal   (+1)
MAX_HEADING_WORDS = 12     # hard gate: longer lines are never headings
CENTER_TOLERANCE = 0.12    # centered if |line center - column center| <= this * width
NARROW_WIDTH_RATIO = 0.60  # line narrower than this fraction of column -> narrow (+1)
HEADING_GAP_FACTOR = 0.80  # gap above > this * median line height -> isolated (+1)
BOLD_CHAR_RATIO = 0.60     # line counts as bold if >= this fraction of chars are bold
HEADING_SCORE = 2          # score threshold to be a heading
MAX_LEVELS = 3             # H1..H3


@dataclass
class LineInfo:
    """A line plus the derived features used to classify it, and the results."""

    text: str
    size: float
    bold: bool
    word_count: int
    bbox: tuple[float, float, float, float]
    gap_above: float = 0.0
    is_heading: bool = False
    level: int = 0                                   # 1..3 heading, 0 body
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
    bold = (bold_chars / total_chars) >= BOLD_CHAR_RATIO

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
    )


def median_line_height(infos: list[LineInfo]) -> float:
    heights = [info.bbox[3] - info.bbox[1] for info in infos if info.bbox[3] > info.bbox[1]]
    return median(heights) if heights else 1.0


def body_font_size(infos: list[LineInfo]) -> float:
    """Char-weighted median size across all lines -> the body text size."""
    return _char_weighted_median([(info.size, len(info.text)) for info in infos])


def _text_bounds(infos: list[LineInfo]) -> tuple[float, float]:
    left = min(info.bbox[0] for info in infos)
    right = max(info.bbox[2] for info in infos)
    return left, right


def _compute_gaps(infos: list[LineInfo]) -> None:
    """Set gap_above for each line from the previous line's bottom (reading order)."""
    prev_bottom = None
    for info in infos:
        top = info.bbox[1]
        info.gap_above = max(0.0, top - prev_bottom) if prev_bottom is not None else 0.0
        prev_bottom = info.bbox[3]


import re

HEADING_NUMBER_RE = re.compile(
    r"^((chapter|section|appendix)\s+\w+|(\d+(\.\d+)*))",
    re.IGNORECASE,
)

ENDING_PUNCTUATION = {".", ",", ";", ":", "?", "!"}


def _is_heading(
    info: LineInfo,
    body: float,
    bounds: tuple[float, float],
    median_lh: float,
) -> bool:
    """
    Returns True if a line is likely to be a heading.

    Combines:
        • Typography
        • Layout
        • Whitespace
        • Textual patterns
    """

    text = info.text.strip()

    if not text:
        return False

    # ------------------------------------------------------------------
    # Hard rejects
    # ------------------------------------------------------------------

    if info.word_count == 0:
        return False

    if info.word_count > MAX_HEADING_WORDS:
        return False

    # Extremely long headings are almost always paragraphs
    if len(text) > 180:
        return False

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    left, right = bounds
    column_width = max(right - left, 1)

    line_width = info.bbox[2] - info.bbox[0]
    width_ratio = line_width / column_width

    line_center = (info.bbox[0] + info.bbox[2]) / 2
    column_center = (left + right) / 2

    centered = (
        abs(line_center - column_center)
        <= CENTER_TOLERANCE * column_width
    )

    narrow = width_ratio < NARROW_WIDTH_RATIO

    # ------------------------------------------------------------------
    # Typography
    # ------------------------------------------------------------------

    size_ratio = info.size / body if body else 1.0

    # ------------------------------------------------------------------
    # Whitespace
    # ------------------------------------------------------------------

    isolated = info.gap_above > median_lh * HEADING_GAP_FACTOR

    # ------------------------------------------------------------------
    # Text features
    # ------------------------------------------------------------------

    numbered = bool(HEADING_NUMBER_RE.match(text))

    all_caps = (
        len(text) > 3
        and text.upper() == text
        and any(c.isalpha() for c in text)
    )

    ends_clean = text[-1] not in ENDING_PUNCTUATION

    title_case = (
        text.istitle()
        and info.word_count <= 8
    )

    # ------------------------------------------------------------------
    # Weighted scoring
    # ------------------------------------------------------------------

    score = 0

    # Font size
    if size_ratio >= 1.6:
        score += 4
    elif size_ratio >= 1.35:
        score += 3
    elif size_ratio >= 1.15:
        score += 2

    # Bold
    if info.bold:
        score += 2

    # Layout
    if centered:
        score += 1

    if narrow:
        score += 1

    if isolated:
        score += 2

    # Text patterns
    if numbered:
        score += 3

    if all_caps:
        score += 2

    if title_case:
        score += 1

    if ends_clean:
        score += 1

    # Small penalty for very long lines
    if info.word_count > 10:
        score -= 2

    return score >= 6


def _assign_levels(infos: list[LineInfo]) -> None:
    """Rank distinct heading sizes: largest -> H1, next -> H2, capped at MAX_LEVELS."""
    sizes = sorted({round(i.size * 2) / 2 for i in infos if i.is_heading}, reverse=True)
    rank = {s: min(idx + 1, MAX_LEVELS) for idx, s in enumerate(sizes)}
    for info in infos:
        if info.is_heading:
            info.level = rank[round(info.size * 2) / 2]


def _assign_paths(infos: list[LineInfo]) -> None:
    """Walk lines, keep a heading stack, give each line its section path."""
    stack: list[tuple[int, str]] = []  # (level, text)
    for info in infos:
        if info.is_heading:
            while stack and stack[-1][0] >= info.level:
                stack.pop()
            info.section_path = [t for _, t in stack]  # parent path (excludes self)
            stack.append((info.level, info.text.strip()))
        else:
            info.section_path = [t for _, t in stack]


def build_sections(lines: list[Line]) -> list[LineInfo]:
    """Classify lines into headings/body, assign levels and section paths.

    Returns list[LineInfo] in reading order, ready for blocks.py.
    """
    infos = [_line_info(line) for line in lines if line.text.strip()]
    if not infos:
        return []

    _compute_gaps(infos)
    body = body_font_size(infos)
    bounds = _text_bounds(infos)
    median_lh = median_line_height(infos)

    for info in infos:
        info.is_heading = _is_heading(info, body, bounds, median_lh)

    _assign_levels(infos)
    _assign_paths(infos)
    return infos