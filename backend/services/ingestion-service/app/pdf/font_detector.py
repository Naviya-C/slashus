import pymupdf, re

from app.sinhala.font_mapping import LEGACY_FONT_PATTERNS, _normalise_font_name, _resolve_mapping

def detect_legacy_font(pdf_path: str) -> tuple[bool, str]:
    doc = pymupdf.open(pdf_path)
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_name = _normalise_font_name(span.get("font", ""))
                    for pat in LEGACY_FONT_PATTERNS:
                        if re.search(pat, font_name):
                            doc.close()
                            return True, _resolve_mapping(font_name)
    doc.close()
    return False, ""