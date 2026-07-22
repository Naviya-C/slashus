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
- Dependency injection via IngestDeps: tests pass fakes (no LLM, no network),
  production passes real adapters.
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
from src.ingestion.models.chunk import Chunk, ChunkType
from src.ingestion.chunking.fallback_splitter import recursive_split
from src.ingestion.chunking.token_estimate import estimate_tokens

log = logging.getLogger(__name__)


@dataclass
class IngestDeps:
    """The ports the pipeline calls through. Pass fakes in tests, real in prod.
    No tokenizer -- Gemini embeds, so chunk sizing is a local estimate."""
    converter: object     # FontConverter
    summarizer: object    # TableSummarizer
    captioner: object     # ImageCaptioner
    storage: object       # Storage
    ocr: object | None = None  # OCREngine (deferred)


def _span_in_tables(bbox, table_bboxes) -> bool:
    """True if a span's center falls inside any detected table region."""
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    for tb in table_bboxes:
        if tb[0] <= cx <= tb[2] and tb[1] <= cy <= tb[3]:
            return True
    return False


def _overlaps(a, b) -> bool:
    """True if two bboxes overlap at all (used to spare heading spans from dedup)."""
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def _dedup_table_bboxes(tables) -> list:
    """Drop tables fully contained inside another (pdfplumber returns nested grids)."""
    boxes = [t.bbox for t in tables]
    kept = []
    for i, a in enumerate(boxes):
        contained = any(
            j != i and b[0] <= a[0] + 1 and b[1] <= a[1] + 1
            and b[2] >= a[2] - 1 and b[3] >= a[3] - 1
            for j, b in enumerate(boxes)
        )
        if not contained:
            kept.append(a)
    return kept


def _tables_for_page(tables, pageno, index, deps, doc_id, next_index):
    """`tables` were already extracted by _process_page — extraction used to run
    TWICE per page (once for regions, once here), doubling pdfplumber work."""
    chunks: list[Chunk] = []
    try:
        summarized = summarize_tables(tables, deps.summarizer)
    except Exception:
        log.warning("table extraction failed on page %s", pageno, exc_info=True)
        return chunks
    for k, st in enumerate(summarized):
        try:
            chunks.append(table_to_chunk(
                st, page=pageno, chunk_index=next_index + len(chunks),
                section_path=index.path_for(st.table.bbox[1]),   # y-position section
                table_id=f"{doc_id}_t{pageno}_{k}",
            ))
        except Exception:
            log.warning("table->chunk failed on page %s", pageno, exc_info=True)
    return chunks


def _images_for_page(fpage, pageno, index, deps, user_id, doc_id, next_index):
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
        url = None
        try:
            url = deps.storage.put(key, img.data)   # put() returns the locator
        except Exception:
            log.warning("image store failed on page %s", pageno, exc_info=True)
            key = None
        keys.append((key, url))

    try:
        captioned = caption_images(images, deps.captioner)
    except Exception:
        log.warning("captioning failed on page %s", pageno, exc_info=True)
        return chunks

    for j, cim in enumerate(captioned):
        try:
            chunks.append(image_to_chunk(
                cim, page=pageno, chunk_index=next_index + len(chunks),
                section_path=index.path_for(cim.image.bbox[1]),   # y-position section
                storage_key=keys[j][0], storage_url=keys[j][1],
                image_id=f"img_{pageno}_{j}",
            ))
        except Exception:
            log.warning("image->chunk failed on page %s", pageno, exc_info=True)
    return chunks


def _ocr_page(fpage, pageno, deps, max_tokens, start_index, section_stack):
    """Scanned page -> OCR text -> budget-sized TEXT chunks.

    OCR gives no font sizes, so heading detection is impossible here; chunks
    inherit the section breadcrumb carried over from the last digital page
    (section_stack). If the whole document is scanned, that stack stays empty
    and these chunks have no title — see embedding/cleaning.py, which can
    drop or keep untitled chunks at store time.
    """
    try:
        text = deps.ocr.read(fpage)
    except Exception:
        log.warning("OCR failed on page %s", pageno, exc_info=True)
        return []
    if not text:
        return []

    breadcrumb = [str(h) for h in section_stack] if section_stack else []
    pieces = recursive_split(text, estimate_tokens, max_tokens)
    return [
        Chunk(
            text=p,
            embed_text=p,
            type=ChunkType.TEXT,
            section_path=list(breadcrumb),
            page=pageno,
            bbox=None,
            chunk_index=start_index + i,
            token_count=estimate_tokens(p),
            extra={"ocr": True},
        )
        for i, p in enumerate(pieces)
    ]


def _process_page(fpage, plumber_page, pageno, deps, user_id, doc_id, max_tokens, start_index,
                  section_stack):
    result = classify_page(fpage)
    if result.decision is PageType.EMPTY:
        return [], section_stack
    if result.decision is PageType.SCANNED:
        if deps.ocr is None:
            log.info("scanned page %s skipped (no OCR wired)", pageno)
            return [], section_stack
        return _ocr_page(fpage, pageno, deps, max_tokens, start_index,
                         section_stack), section_stack

    # --- tables first: pdfplumber owns table detection; get their regions ---
    try:
        tables = extract_tables(fpage, plumber_page, deps.converter)
    except Exception:
        log.warning("table detect failed on page %s", pageno, exc_info=True)
        tables = []
    table_regions = _dedup_table_bboxes(tables)

    # --- read + convert ALL spans EXACTLY ONCE. convert_spans mutates spans in
    #     place, so a second pass would double-convert (e.g. "1." -> "1ග"). We
    #     detect headings on the full set, then filter the resulting INFOS -- never
    #     re-convert. ---
    all_spans = read_spans(fpage)
    all_lines = convert_spans(all_spans, deps.converter)   # the ONLY conversion
    infos, index = build_sections(all_lines, section_stack)

    # keep an info if it is NOT inside a table region, OR it is a heading that
    # happens to sit inside a falsely-detected table box (e.g. a page-number cell)
    body_infos = [
        i for i in infos
        if i.is_heading or not _span_in_tables(i.bbox, table_regions)
    ]

    blocks = build_blocks(body_infos)
    for b in blocks:                                  # assign section BY POSITION
        b.section_path = index.path_for(b.bbox[1])

    page_chunks = chunk_blocks(blocks, page=pageno, max_tokens=max_tokens, start_index=start_index)
    page_chunks += _tables_for_page(tables, pageno, index, deps,
                                    doc_id, start_index + len(page_chunks))
    page_chunks += _images_for_page(fpage, pageno, index, deps,
                                    user_id, doc_id, start_index + len(page_chunks))
    return page_chunks, index.final_stack


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
    section_stack: list = []          # open headings carried across pages
    fdoc = fitz.open(pdf_path) 
    pdoc = pdfplumber.open(pdf_path)
    try:
        for i, fpage in enumerate(fdoc):
            pageno = i + 1
            try:
                page_chunks, section_stack = _process_page(
                    fpage, pdoc.pages[i], pageno, deps, user_id, doc_id,
                    max_tokens, start_index=len(all_chunks), section_stack=section_stack,
                )
                all_chunks.extend(page_chunks)
            except Exception:
                log.warning("page %s failed; skipping", pageno, exc_info=True)
    finally:
        pdoc.close()
        fdoc.close()

    _stamp(all_chunks, doc_id, user_id, source_name)
    return all_chunks