"""
pipeline/deps.py
================

PURPOSE
-------
Build IngestDeps, choosing REAL adapters where they are configured/available and
NULL fallbacks otherwise. So:

    ingest(pdf, ..., deps=default_deps())                    # zero services
    ingest(pdf, ..., deps=default_deps(gemini_key=KEY))      # real LLMs
    ingest(pdf, ..., deps=default_deps(gemini_key=KEY, storage=r2))  # + cloud

Each real adapter is constructed defensively: if piliwela isn't built, or the
Gemini SDK/key is missing, we log and drop to the null fallback instead of
crashing. Nothing here raises just because a service is absent.
"""

from __future__ import annotations

import logging

from src.ingestion.pipeline.ingest import IngestDeps                           
from src.ingestion.adapters.null_adapters import NullConverter, NullSummarizer, NullCaptioner  
from src.ingestion.adapters.local_storage import LocalStorage                 

log = logging.getLogger(__name__)


def _safe(factory, fallback, name):
    """Construct a real adapter, or fall back if it isn't available."""
    try:
        return factory()
    except Exception:
        log.info("%s unavailable; using fallback", name)
        return fallback


def default_deps(*, gemini_key: str | None = None, storage=None, store_dir: str = "./_store") -> IngestDeps:
    """Assemble deps: real where configured, null where not."""
    # font converter: piliwela if the build is present, else passthrough
    def _converter():
        from src.ingestion.extraction.span_converter import PiliwelaConverter    
        return PiliwelaConverter()
    converter = _safe(_converter, NullConverter(), "piliwela")

    # LLMs: only if a key is given (and the SDK is importable)
    if gemini_key:
        def _sum():
            from llm_summarizer import GeminiTableSummarizer
            return GeminiTableSummarizer(api_key=gemini_key)

        def _cap():
            from llm_captioner import GeminiImageCaptioner
            return GeminiImageCaptioner(api_key=gemini_key)

        summarizer = _safe(_sum, NullSummarizer(), "gemini summarizer")
        captioner = _safe(_cap, NullCaptioner(), "gemini captioner")
    else:
        summarizer, captioner = NullSummarizer(), NullCaptioner()

    # storage: caller-provided (e.g. cloud) or local disk
    storage = storage or LocalStorage(store_dir)

    return IngestDeps(
        converter=converter,
        summarizer=summarizer,
        captioner=captioner,
        storage=storage,
    )