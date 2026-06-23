from dataclasses import dataclass
from typing import Optional

@dataclass
class ProcessPDF:
    pdf_path: str
    output_json_path: str
    image_output_dir: Optional[str] = None
    start_page: int = 0
    end_page: Optional[int] = None
    api_key: Optional[str] = None
    force_legacy_mapping: Optional[str] = None