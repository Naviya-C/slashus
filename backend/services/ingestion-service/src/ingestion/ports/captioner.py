"""
ports/captioner.py
==================

PURPOSE
-------
The seam between the pipeline and whatever vision LLM captions images. The
enrichment stage depends on THIS interface, never on the Gemini SDK directly --
so it runs in tests against a fake, and the model/provider can change without
touching pipeline code.

THE CONTRACT
------------
    caption(image_bytes, mime_type, context="") -> str

Given the raw image bytes, its mime type, and optional grounding context (the
nearby caption line + the section title), return a SHORT description of what the
image shows. That description is BOTH the image chunk's content and what gets
embedded for retrieval.
"""

from __future__ import annotations

from typing import Protocol


class ImageCaptioner(Protocol):
    def caption(self, image_bytes: bytes, mime_type: str, context: str = "") -> str:
        ...