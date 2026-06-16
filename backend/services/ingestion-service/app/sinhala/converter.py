from pandukabhaya import PandukabhayaConverter
from typing import Optional

from font_mapping import looks_like_legacy_ascii_sinhala

class SinhalaTextConverter:
    def __init__(self, is_legacy: bool, mapping: str = "fm_abhaya"):
        self.is_legacy = is_legacy
        self.mapping = mapping
        self._converter: Optional[PandukabhayaConverter] = None
        if is_legacy:
            try:
                self._converter = PandukabhayaConverter(mapping)
                print(f"Legacy font detected → Pandukabhaya loaded (mapping: {mapping})")
            except FileNotFoundError:
                print(f"Mapping '{mapping}' not found. Falling back to fm_abhaya.")
                self._converter = PandukabhayaConverter("fm_abhaya")

    def convert(self, text: str) -> str:
        if self._converter is not None:
            return self._converter.convert(text)
        if looks_like_legacy_ascii_sinhala(text):
            return PandukabhayaConverter("fm_abhaya").convert(text)
        return text
