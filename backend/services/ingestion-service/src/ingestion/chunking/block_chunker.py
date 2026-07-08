"""
chunking/block_chunker.py
=========================

PURPOSE
-------
Block-wise chunking: ONE chunk per block. If a block exceeds the budget,
recursively split THAT block (and only that block) into budget-sized pieces.

    for each paragraph block:
        n = estimate_tokens(block)
        n <= budget  -> one chunk
        n >  budget  -> recursive_split(block) -> several chunks

Headings are NOT emitted as chunks -- they already live in each block's
section_path (the breadcrumb). Chunking is per page, so every chunk has one clean
page number (page boundaries are hard by construction).

SIZING WITHOUT A TOKENIZER
--------------------------
Gemini does the embeddings, so we don't load a HF tokenizer. The budget is
measured with a local word-based estimate (token_estimate.estimate_tokens). You
can still inject a precise counter via `count=` if you ever need exactness.
"""

from __future__ import annotations

from src.ingestion.layout.blocks import Block
from src.ingestion.models.chunk import Chunk, ChunkType
from src.ingestion.chunking.fallback_splitter import recursive_split
from src.ingestion.chunking.token_estimate import estimate_tokens


DEFAULT_MAX_TOKENS = 720  # approximate word budget; keep below Gemini's real limit
MIN_CHUNK_TOKENS = 5      # drop sub-threshold paragraph blocks (page numbers, stray labels)


def _is_noise(text: str, count, min_tokens: int) -> bool:
    """A paragraph block too small to be a useful retrieval unit.

    Page numbers, ISBN fragments, and 1-2 word stray labels become their own
    PyMuPDF blocks. They add noise to retrieval, so we drop paragraph blocks under
    min_tokens. Headings/tables/images are never routed here, so they are
    unaffected. A block that is purely digits/punctuation is always noise.
    min_tokens <= 0 disables filtering.
    """
    stripped = text.strip()
    if not stripped:
        return True
    if min_tokens <= 0:
        return False
    if all(not c.isalpha() for c in stripped):   # digits / punctuation only
        return True
    return count(stripped) < min_tokens


def _embed_text(text: str, section_path: list[str]) -> str:
    """Prepend the section breadcrumb before embedding (a cheap retrieval win)."""
    if section_path:
        return " > ".join(section_path) + "\n\n" + text
    return text


def chunk_blocks(
    blocks: list[Block],
    *,
    page: int | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    min_tokens: int = MIN_CHUNK_TOKENS,
    start_index: int = 0,
    count=estimate_tokens,
) -> list[Chunk]:
    """Chunk a page's blocks block-wise, with recursive fallback on oversized blocks.

    Args:
        blocks: paragraph/heading Blocks from blocks.build_blocks (one page).
        page: the page number these blocks came from.
        max_tokens: budget per chunk.
        min_tokens: paragraph blocks smaller than this are dropped as noise.
        start_index: chunk_index to start from (so pages number continuously).
        count: token estimator (defaults to the local word-based estimate).

    Returns:
        list[Chunk] for this page.
    """
    chunks: list[Chunk] = []
    idx = start_index

    for block in blocks:
        if block.kind != "paragraph":
            continue  # headings live in section_path, not as chunks

        if _is_noise(block.text, count, min_tokens):
            continue  # page numbers, stray labels -- not useful retrieval units

        n = count(block.text)
        pieces = [block.text] if n <= max_tokens else recursive_split(block.text, count, max_tokens)

        for piece in pieces:
            chunks.append(
                Chunk(
                    text=piece,
                    embed_text=_embed_text(piece, block.section_path),
                    type=ChunkType.TEXT,
                    section_path=list(block.section_path),
                    page=page,
                    bbox=block.bbox,
                    chunk_index=idx,
                    token_count=count(piece),
                )
            )
            idx += 1

    return chunks
