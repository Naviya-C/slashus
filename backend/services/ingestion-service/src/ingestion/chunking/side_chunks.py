"""
chunking/side_chunks.py
=======================

PURPOSE
-------
Turn the side-channel outputs into the ONE Chunk shape, so tables and images sit
in the pipeline exactly like text chunks.

    table  (SummarizedTable) -> Chunk: text=markdown, embed_text=summary, type=TABLE
    image  (CaptionedImage)  -> Chunk: text=caption,  embed_text=caption,  type=IMAGE

Sizing uses the same local word-based estimate as the chunker (no tokenizer,
since Gemini embeds).
"""

from __future__ import annotations

from src.ingestion.models.chunk import Chunk, ChunkType
from src.ingestion.enrichment.summarize_tables import SummarizedTable
from src.ingestion.enrichment.caption_images import CaptionedImage
from src.ingestion.chunking.token_estimate import estimate_tokens


def table_to_chunk(
    summarized: SummarizedTable,
    *,
    page: int | None = None,
    chunk_index: int = 0,
    section_path: list[str] | None = None,
    table_id: str | None = None,
) -> Chunk:
    """SummarizedTable -> Chunk. Content is the markdown; the summary is embedded."""
    table = summarized.table
    return Chunk(
        text=table.markdown,
        embed_text=summarized.summary,
        type=ChunkType.TABLE,
        section_path=list(section_path or []),
        page=page,
        bbox=table.bbox,
        chunk_index=chunk_index,
        token_count=estimate_tokens(table.markdown),
        extra={"table_id": table_id, "n_rows": table.n_rows, "n_cols": table.n_cols},
    )


def image_to_chunk(
    captioned: CaptionedImage,
    *,
    page: int | None = None,
    chunk_index: int = 0,
    section_path: list[str] | None = None,
    storage_key: str | None = None,
    storage_url: str | None = None,
    image_id: str | None = None,
) -> Chunk:
    """CaptionedImage -> Chunk. Caption is both the content and what gets embedded."""
    image = captioned.image
    return Chunk(
        text=captioned.caption,
        embed_text=captioned.caption,
        type=ChunkType.IMAGE,
        section_path=list(section_path or []),
        page=page,
        bbox=image.bbox,
        chunk_index=chunk_index,
        token_count=estimate_tokens(captioned.caption),
        extra={"image_id": image_id, "storage_key": storage_key,
               "storage_url": storage_url,
               "width": image.width, "height": image.height},
    )
