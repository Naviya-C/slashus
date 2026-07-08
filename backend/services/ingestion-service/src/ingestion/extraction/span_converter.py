"""
extraction/span_converter.py
============================

PURPOSE
-------
Take the RAW spans from span_reader and produce CLEAN, reassembled lines:
legacy Sinhala becomes Unicode, English stays exactly as it is, order preserved.

Two steps:
    1. Convert each span in place by handing (text, font) to piliwela.
       piliwela decides everything (legacy Sinhala -> Unicode; anything else,
       including English typed in an FM font, comes back unchanged via its
       dictionary filter). This loop has NO language logic of its own.
    2. Reassemble same-line spans back into one clean line, in reading order.

The converter is INJECTABLE: real code uses the built-in PiliwelaConverter;
tests pass a fake. piliwela is imported lazily inside the adapter, so this module
still imports (and the fake-based tests still run) on a machine without the Rust
build.
"""

from __future__ import annotations

from dataclasses import dataclass

from .span_reader import Span  # -> ingestion.extraction.span_reader in the tree


# --------------------------------------------------------------------------- #
# The real converter: piliwela behind the (text, font) -> str contract.
# --------------------------------------------------------------------------- #
class PiliwelaConverter:
    """Real FontConverter. Wraps piliwela's span-level API.

    piliwela handles the routing internally: legacy font -> convert, otherwise
    return the text unchanged. So we simply forward every span to it.
    """

    def __init__(self) -> None:
        import piliwela  # lazy: importing this module never requires the build
        self._piliwela = piliwela

    def convert(self, text: str, font: str) -> str:
        return self._piliwela.convert_auto_with_metadata(text, font)


# --------------------------------------------------------------------------- #
# Output model.
# --------------------------------------------------------------------------- #
@dataclass
class Line:
    """One reassembled line of clean text plus the converted spans it came from
    (spans kept so the layout stage can do heading detection)."""

    text: str
    spans: list[Span]
    block_no: int
    line_no: int


# --------------------------------------------------------------------------- #
# The stage.
# --------------------------------------------------------------------------- #
def convert_spans(spans: list[Span], converter=None) -> list[Line]:
    """Convert every span in place, then reassemble into clean lines.

    Args:
        spans: raw spans from span_reader (reading order, grouped by line).
        converter: anything with convert(text, font) -> str. Defaults to the
                   real PiliwelaConverter; pass a fake in tests.

    Returns:
        list[Line] of clean, reassembled lines in reading order.
    """
    if converter is None:
        converter = PiliwelaConverter()

    # 1. Convert in place. Whitespace-only spans are skipped (nothing to convert,
    #    and they carry the spacing between words).
    for span in spans:
        if span.text.strip():
            span.text = converter.convert(span.text, span.font)

    # 2. Reassemble lines using the grouping span_reader preserved.
    return _group_into_lines(spans)


def _group_into_lines(spans: list[Span]) -> list[Line]:
    """Join consecutive same-line spans into Line objects, in order."""
    lines: list[Line] = []
    bucket: list[Span] = []
    current_key: tuple[int, int] | None = None

    for span in spans:
        key = (span.block_no, span.line_no)
        if bucket and key != current_key:
            lines.append(_make_line(bucket))
            bucket = []
        current_key = key
        bucket.append(span)

    if bucket:
        lines.append(_make_line(bucket))

    return lines


def _make_line(spans: list[Span]) -> Line:
    """Build one Line from a group of same-line spans (join with '' to keep the
    spacing the spans already contain)."""
    return Line(
        text="".join(s.text for s in spans),
        spans=list(spans),
        block_no=spans[0].block_no,
        line_no=spans[0].line_no,
    )