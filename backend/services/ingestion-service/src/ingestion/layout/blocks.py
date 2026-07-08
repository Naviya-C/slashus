"""
layout/blocks.py
================

PURPOSE
-------
Turn the classified lines from sections.py into BLOCKS -- the units the chunker
works with. Two kinds:
    heading   : one heading line, with its level and parent section path.
    paragraph : the lines of ONE source block, merged into one text block.

REBUILDING PARAGRAPHS (the fix)
-------------------------------
A paragraph's lines share the SAME PyMuPDF block_no, so we regroup lines by
block_no -- this reassembles the whole paragraph as one block, which is exactly
what "block-wise" chunking means. We do NOT rely on the vertical-gap heuristic as
the primary signal (it over-split paragraphs with loose line spacing, producing
one fragment chunk per line).

A paragraph block ends when:
    * a heading appears        (hard boundary), or
    * the section path changes (crossed into a new section), or
    * the block_no changes     (a new source block = a new paragraph), or
    * there is a VERY large vertical gap  (safety net for when PyMuPDF lumps two
      paragraphs into one block_no).

WHAT IT DOES NOT DO
-------------------
No token counting, no chunk sizing, no overlap -- that's the chunker. Pure
function over LineInfo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.ingestion.layout.sections import LineInfo, median_line_height


# Only a genuinely LARGE gap breaks a paragraph now (safety net, not the primary
# rule). Set high so normal / loose line spacing never fragments a paragraph.
PARA_BREAK_GAP_FACTOR = 2.0


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
    """Merge body lines into paragraphs (by source block_no), headings stay separate."""
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
            same_block = info.block_no == prev.block_no
            huge_gap = info.gap_above > break_gap
            # Break only on a real boundary -- NOT on ordinary line spacing.
            if not same_section or not same_block or huge_gap:
                flush()

        para.append(info)

    flush()
    return blocks
