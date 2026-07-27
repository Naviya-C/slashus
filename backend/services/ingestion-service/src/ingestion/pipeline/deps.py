"""
pipeline/deps.py
================

PURPOSE
-------
Build IngestDeps, choosing REAL adapters where they are configured/available and
NULL fallbacks otherwise.

The storage implementation is selected by the shared storage factory based on
configuration (e.g. STORAGE_PROVIDER). The ingestion pipeline itself remains
agnostic to whether storage is Local, GCS, S3, etc.
"""

from __future__ import annotations

import logging

from src.ingestion.pipeline.ingest import IngestDeps
from src.ingestion.adapters.null_adapters import (
    NullConverter,
    NullSummarizer,
    NullCaptioner,
)

from storage import create_store

log = logging.getLogger(__name__)


def _safe(factory, fallback, name):
    """Construct a real adapter, or fall back if it isn't available."""
    try:
        return factory()
    except Exception:
        log.info("%s unavailable; using fallback", name)
        return fallback


def default_deps(
    *,
    gemini_key: str | None = None,
    storage = None,
    ocr: bool = True,
) -> IngestDeps:
    """Assemble dependencies for the ingestion pipeline."""

    # ------------------------------------------------------------------
    # Font converter
    # ------------------------------------------------------------------

    def _converter():
        from src.ingestion.extraction.span_converter import PiliwelaConverter

        return PiliwelaConverter()

    converter = _safe(_converter, NullConverter(), "piliwela")

    # ------------------------------------------------------------------
    # LLM adapters
    # ------------------------------------------------------------------

    if gemini_key:

        def _sum():
            from src.ingestion.adapters.llm_summarizer import GeminiTableSummarizer

            return GeminiTableSummarizer(api_key=gemini_key)

        def _cap():
            from src.ingestion.adapters.llm_captioner import GeminiImageCaptioner

            return GeminiImageCaptioner(api_key=gemini_key)

        summarizer = _safe(_sum, NullSummarizer(), "gemini summarizer")
        captioner = _safe(_cap, NullCaptioner(), "gemini captioner")
    else:
        summarizer = NullSummarizer()
        captioner = NullCaptioner()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    if storage is None:
        storage = _safe(
            create_store,
            None,
            "object storage",
        )

    if storage is None:
        raise RuntimeError("Unable to initialize object storage")

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    ocr_engine = None
    if ocr:

        def _ocr():
            from src.ingestion.adapters.tesseract_ocr import TesseractOCR

            return TesseractOCR()

        ocr_engine = _safe(_ocr, None, "tesseract ocr")

    # ------------------------------------------------------------------
    # Build dependency container
    # ------------------------------------------------------------------

    return IngestDeps(
        converter=converter,
        summarizer=summarizer,
        captioner=captioner,
        storage=storage,
        ocr=ocr_engine,
    )