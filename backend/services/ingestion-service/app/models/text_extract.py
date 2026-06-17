# models/page_context.py

from dataclasses import dataclass
from sinhala.converter import SinhalaTextConverter

@dataclass
class PageContext:
    pdf_path: str
    page_number: int
    converter: SinhalaTextConverter