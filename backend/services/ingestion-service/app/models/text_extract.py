from dataclasses import dataclass
from app.sinhala.converter import SinhalaTextConverter

@dataclass
class PageContext:
    pdf_path: str
    page_number: int
    converter: SinhalaTextConverter