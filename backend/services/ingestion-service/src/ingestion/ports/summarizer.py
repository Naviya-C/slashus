"""
ports/summarizer.py
===================

PURPOSE
-------
The seam between the pipeline and whatever LLM writes table summaries. The
enrichment stage depends on THIS interface, never on the Gemini SDK directly --
so it runs in tests against a fake, and the model/provider can change without
touching pipeline code.

THE CONTRACT
------------
    summarize(markdown, context="") -> str

Given a table rendered as markdown (and optional grounding context: the nearby
caption + the section title), return a SHORT one-line description of what the
table shows. That one line is what gets EMBEDDED for retrieval; the markdown
itself stays as the chunk content.
"""

from __future__ import annotations

from typing import Protocol


class TableSummarizer(Protocol):
    def summarize(self, markdown: str, context: str = "") -> str:
        ...