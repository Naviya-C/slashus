"""
layout/blocks.py
================

PURPOSE
-------
Turn the classified lines from sections.py into BLOCKS -- the units the chunker
works with. There are two kinds:

    heading   : one heading line, with its level and parent section path.
    paragraph : consecutive BODY lines merged into one text block.

Merging rule for paragraphs: keep absorbing body lines while they stay in the
SAME section and there is no large vertical gap. A block ends when:
    * a heading appears        (a heading is a hard boundary), or
    * the section path changes (we crossed into a new section), or
    * the gap above a line is large (a blank line -> new paragraph).

This is exactly what the chunker needs: paragraphs to pack, and section
boundaries it must never merge across.

WHAT IT DOES NOT DO 
-------------------
No token counting, no chunk sizing, no overlap -- that's the chunker. This stage
just produces clean, section-tagged blocks. Pure function over LineInfo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .sections import LineInfo
from .sections import median_line_height


# gap above a line greater than this * median line height -> paragraph break
PARA_BREAK_GAP_FACTOR = 0.60


@dataclass
class Block:
    """A heading or a paragraph, tagged with where it sits in the section tree."""

    kind: str                                        # "heading" | "paragraph"
    text: str
    level: int                                       # heading level (0 for paragraph)
    section_path: list[str] = field(default_factory=list)
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)


def _union_bbox(infos: list[LineInfo]) -> tuple[float, float, float, float]:
    return (
        min(i.bbox[0] for i in infos),
        min(i.bbox[1] for i in infos),
        max(i.bbox[2] for i in infos),
        max(i.bbox[3] for i in infos),
    )


def _paragraph_block(infos: list[LineInfo]) -> Block:
    return Block(
        kind="paragraph",
        text=" ".join(i.text.strip() for i in infos),
        level=0,
        section_path=list(infos[0].section_path),
        bbox=_union_bbox(infos),
    )


def _heading_block(info: LineInfo) -> Block:
    return Block(
        kind="heading",
        text=info.text.strip(),
        level=info.level,
        section_path=list(info.section_path),
        bbox=info.bbox,
    )


def build_blocks(infos: list[LineInfo]) -> list[Block]:
    """Merge body lines into paragraphs, emit headings as their own blocks."""
    if not infos:
        return []

    median_lh = median_line_height(infos)
    break_gap = median_lh * PARA_BREAK_GAP_FACTOR

    blocks: list[Block] = []
    para: list[LineInfo] = []

    def flush() -> None:
        if para:
            blocks.append(_paragraph_block(para))
            para.clear()

    for info in infos:
        if info.is_heading:
            flush()
            blocks.append(_heading_block(info))
            continue

        if para:
            prev = para[-1]
            same_section = info.section_path == prev.section_path
            big_gap = info.gap_above > break_gap
            if not same_section or big_gap:
                flush()

        para.append(info)

    flush()
    return blocks