"""
test.py — tests for span_converter.py
=====================================
Core guarantees: English (Latin font) untouched, Sinhala (FM font) converted,
mixed lines reassembled in order, lines grouped correctly, spacing preserved.

Self-contained: a tiny fake stands in for piliwela so no Rust build is needed.
Run:  python3 -m pytest test.py -v
"""

from src.ingestion.extraction.span_reader import Span
from src.ingestion.extraction.span_converter import convert_spans, Line


class FakeFontConverter:
    """Stand-in for piliwela: a legacy-font span maps known tokens to Unicode;
    everything else (and any non-legacy font) is returned unchanged."""

    def __init__(self, mapping=None, legacy_fonts=("FM", "DL-")):
        self._map = dict(mapping or {})
        self._legacy = tuple(legacy_fonts)

    def convert(self, text, font):
        if font.startswith(self._legacy):
            return self._map.get(text, text)
        return text


def _span(text, font, block_no=0, line_no=0):
    return Span(text=text, font=font, size=12.0, bold=False,
                bbox=(0, 0, 1, 1), block_no=block_no, line_no=line_no)


def test_english_latin_font_untouched():
    spans = [_span("Hello World", "Arial")]
    fake = FakeFontConverter(mapping={"Hello World": "SHOULD_NOT_HAPPEN"})
    lines = convert_spans(spans, fake)
    assert lines[0].text == "Hello World"


def test_sinhala_fm_font_converted():
    spans = [_span("jhsrih", "FMAbhaya")]
    fake = FakeFontConverter(mapping={"jhsrih": "වයිරසය"})
    lines = convert_spans(spans, fake)
    assert lines[0].text == "වයිරසය"


def test_mixed_line_order_preserved():
    spans = [
        _span("COVID-19 ", "Arial"),
        _span("jhsrih ",   "FMAbhaya"),
        _span("PCR ",      "Arial"),
        _span("mrSlaIKh",  "FMAbhaya"),
    ]
    fake = FakeFontConverter(mapping={"jhsrih ": "වයිරසය ", "mrSlaIKh": "පරීක්ෂණය"})
    lines = convert_spans(spans, fake)
    assert len(lines) == 1
    assert lines[0].text == "COVID-19 වයිරසය PCR පරීක්ෂණය"


def test_lines_grouped_by_block_and_line():
    spans = [
        _span("first", "Arial", block_no=0, line_no=0),
        _span("second", "Arial", block_no=0, line_no=1),
    ]
    lines = convert_spans(spans, FakeFontConverter())
    assert len(lines) == 2
    assert lines[0].text == "first"
    assert lines[1].text == "second"


def test_whitespace_span_preserved():
    spans = [
        _span("wpqj ", "FMAbhaya"),
        _span(" ", "FMAbhaya"),
        _span("wjika", "FMAbhaya"),
    ]
    fake = FakeFontConverter(mapping={"wpqj ": "අවුරුදු ", "wjika": "අවසන"})
    lines = convert_spans(spans, fake)
    assert lines[0].text == "අවුරුදු  අවසන"


def test_returns_line_objects():
    lines = convert_spans([_span("x", "Arial")], FakeFontConverter())
    assert isinstance(lines[0], Line)