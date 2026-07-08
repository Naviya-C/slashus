"""
enrichment/summarize_tables.py
==============================

PURPOSE
-------
The enrichment STAGE for tables. Given the Table objects from table_extractor,
attach the embed-summary to each by calling the TableSummarizer port. The
markdown stays as the content; the summary is what will be embedded.

FAILURE ISOLATION
-----------------
An LLM call can fail (network, quota, safety block). One bad table must not kill
a 300-page ingest, so a failed summary falls back to a deterministic description
("Table with N rows and M columns"). The pipeline always moves on.

CACHING (later)
---------------
Summaries are the expensive part and are pure functions of the markdown, so they
should be cached by a hash of the markdown (utils/caching.py) -- the same reused
textbook table then costs one LLM call, not a thousand. Left as a wrap point.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.extraction.table_extractor import Table


@dataclass
class SummarizedTable:
    table: Table
    summary: str


def _fallback(table: Table) -> str:
    return f"Table with {table.n_rows} rows and {table.n_cols} columns."


def summarize_tables(
    tables: list[Table],
    summarizer,
    context: str = "",
) -> list[SummarizedTable]:
    """Attach an embed-summary to each table via the summarizer port.

    Args:
        tables: from table_extractor.extract_tables.
        summarizer: a TableSummarizer (real Gemini adapter, or a fake).
        context: optional grounding text (nearby caption + section title).

    Returns:
        list[SummarizedTable] in the same order.
    """
    out: list[SummarizedTable] = []
    for table in tables:
        try:
            summary = summarizer.summarize(table.markdown, context=context).strip()
            if not summary:
                summary = _fallback(table)
        except Exception:
            summary = _fallback(table)  
        out.append(SummarizedTable(table = table, summary = summary))
    return out