"""
Quality filters applied before embedding.

Untitled chunks are usually layout artifacts (cover pages, headers, footers,
printer marks, etc.). For digital documents they are skipped before embedding.

For fully scanned documents, the embedding pipeline passes
require_title=False so these chunks are retained.
"""

from __future__ import annotations
