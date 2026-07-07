"""
pipeline/ingest.py
==================

PURPOSE
-------
The orchestrator -- the spine that runs every stage in order and returns the
finished chunks. The one entry point every caller (CLI, API, worker) uses:

    ingest(pdf_path, user_id, doc_id, source_name, deps) -> list[Chunk]

FLOW (per page)
---------------
    detect -> digital / scanned / empty
    digital:
        span_reader -> convert_spans -> build_sections -> build_blocks -> chunk_blocks   (text)
        extract_tables -> summarize_tables -> table_to_chunk                              (tables)
        extract_images -> storage.put -> caption_images -> image_to_chunk                 (images)
    scanned: OCR hook (deferred) -- skipped unless deps.ocr is provided
    empty:   skipped

Then all chunks get doc-level fields stamped (chunk_id, doc_id, user_id,
source_name). Embedding + storing into Qdrant is a SEPARATE step (keeps ingest
fast, testable, and re-runnable without re-embedding).

DESIGN
------
- Dependency injection via IngestDeps: tests pass fakes / nulls (no LLM, no
  network), production passes real adapters. See pipeline/deps.default_deps.
- No tokenizer: Gemini embeds, so chunk sizing uses a local word estimate.
- Failure isolation: each page, and each table/image, is wrapped so one bad item
  doesn't kill a long ingest -- it's logged and skipped.

KNOWN LIMITS (later)
--------------------
- Sections are per page (a heading on page 1 doesn't carry to page 2 yet).
- Scanned pages need the OCR stage wired in.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import fitz          # PyMuPDF
import pdfplumber

from src.ingestion.detection.page_type import classify_page, PageType
from src.ingestion.extraction.span_reader import read_spans
from src.ingestion.extraction.span_converter import convert_spans
from src.ingestion.layout.sections import build_sections
from src.ingestion.layout.blocks import build_blocks
from src.ingestion.chunking.block_chunker import chunk_blocks, DEFAULT_MAX_TOKENS
from src.ingestion.extraction.table_extractor import extract_tables
from src.ingestion.enrichment.summarize_tables import summarize_tables
from src.ingestion.extraction.image_extractor import extract_images
from src.ingestion.enrichment.caption_images import caption_images
from src.ingestion.chunking.side_chunks import table_to_chunk, image_to_chunk
from src.ingestion.ports.storage import image_key
from src.ingestion.models.chunk import Chunk

log = logging.getLogger(__name__)


@dataclass
class IngestDeps:
    """The ports the pipeline calls through. Pass fakes/nulls in tests, real in prod.
    No tokenizer -- Gemini embeds, so chunk sizing is a local estimate."""
    converter: object     # FontConverter
    summarizer: object    # TableSummarizer
    captioner: object     # ImageCaptioner
    storage: object       # Storage
    ocr: object | None = None  # OCREngine (deferred)


def _section_for_bbox(bbox, blocks) -> list[str]:
    """Best-effort section path for a table/image: the section of the last block
    that starts at or above it (headings include their own text)."""
    top = bbox[1]
    eff: list[str] = []
    for b in blocks:
        if b.bbox[1] <= top + 1:
            eff = list(b.section_path) + ([b.text] if b.kind == "heading" else [])
        else:
            break
    return eff


def _tables_for_page(fpage, plumber_page, pageno, blocks, deps, doc_id, next_index):
    chunks: list[Chunk] = []
    try:
        tables = extract_tables(fpage, plumber_page, deps.converter)
        summarized = summarize_tables(tables, deps.summarizer)
    except Exception:
        log.warning("table extraction failed on page %s", pageno, exc_info=True)
        return chunks
    for k, st in enumerate(summarized):
        try:
            chunks.append(table_to_chunk(
                st, page=pageno, chunk_index=next_index + len(chunks),
                section_path=_section_for_bbox(st.table.bbox, blocks),
                table_id=f"{doc_id}_t{pageno}_{k}",
            ))
        except Exception:
            log.warning("table->chunk failed on page %s", pageno, exc_info=True)
    return chunks


def _images_for_page(fpage, pageno, blocks, deps, user_id, doc_id, next_index):
    chunks: list[Chunk] = []
    try:
        images = extract_images(fpage)
    except Exception:
        log.warning("image extraction failed on page %s", pageno, exc_info=True)
        return chunks

    # store bytes first (per-image isolation), remember the keys
    keys: list[str | None] = []
    for j, img in enumerate(images):
        key = image_key(user_id, doc_id, f"img_{pageno}_{j}", img.ext)
        try:
            deps.storage.put(key, img.data)
        except Exception:
            log.warning("image store failed on page %s", pageno, exc_info=True)
            key = None
        keys.append(key)

    try:
        captioned = caption_images(images, deps.captioner)
    except Exception:
        log.warning("captioning failed on page %s", pageno, exc_info=True)
        return chunks

    for j, cim in enumerate(captioned):
        try:
            chunks.append(image_to_chunk(
                cim, page=pageno, chunk_index=next_index + len(chunks),
                section_path=_section_for_bbox(cim.image.bbox, blocks),
                storage_key=keys[j], image_id=f"img_{pageno}_{j}",
            ))
        except Exception:
            log.warning("image->chunk failed on page %s", pageno, exc_info=True)
    return chunks


def _process_page(fpage, plumber_page, pageno, deps, user_id, doc_id, max_tokens, start_index):
    result = classify_page(fpage)
    if result.decision is PageType.EMPTY:
        return []
    if result.decision is PageType.SCANNED:
        if deps.ocr is None:
            log.info("scanned page %s skipped (no OCR wired)", pageno)
        # OCR hook: deps.ocr.read(fpage) -> text -> block -> chunk (deferred)
        return []

    # DIGITAL path
    spans = read_spans(fpage)
    lines = convert_spans(spans, deps.converter)
    infos = build_sections(lines)
    blocks = build_blocks(infos)

    page_chunks = chunk_blocks(blocks, page=pageno, max_tokens=max_tokens, start_index=start_index)
    page_chunks += _tables_for_page(fpage, plumber_page, pageno, blocks, deps,
                                    doc_id, start_index + len(page_chunks))
    page_chunks += _images_for_page(fpage, pageno, blocks, deps,
                                    user_id, doc_id, start_index + len(page_chunks))
    return page_chunks


def _stamp(chunks: list[Chunk], doc_id: str, user_id: str, source_name: str) -> None:
    """Add doc-level fields onto every chunk's extra (promote to fields if you like)."""
    for c in chunks:
        c.extra.update({
            "chunk_id": f"{doc_id}:{c.chunk_index}",
            "doc_id": doc_id,
            "user_id": user_id,
            "source_name": source_name,
        })


def ingest(
    pdf_path: str,
    *,
    user_id: str,
    doc_id: str,
    source_name: str,
    deps: IngestDeps,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[Chunk]:
    """Run the whole pipeline on a PDF and return its chunks (unembedded)."""
    all_chunks: list[Chunk] = []
    fdoc = fitz.open(pdf_path)
    pdoc = pdfplumber.open(pdf_path)
    try:
        for i, fpage in enumerate(fdoc):
            pageno = i + 1
            try:
                page_chunks = _process_page(
                    fpage, pdoc.pages[i], pageno, deps, user_id, doc_id,
                    max_tokens, start_index=len(all_chunks),
                )
                all_chunks.extend(page_chunks)
            except Exception:
                log.warning("page %s failed; skipping", pageno, exc_info=True)
    finally:
        pdoc.close()
        fdoc.close()

    _stamp(all_chunks, doc_id, user_id, source_name)
    return all_chunks