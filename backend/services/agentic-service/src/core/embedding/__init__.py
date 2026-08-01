"""Language detection only.

The dense and sparse encoders moved to embedding-service, which owns the
model and the vocab. This package keeps script-based language detection,
which needs neither.
"""

from core.embedding.language import detect_language

__all__ = ["detect_language"]
