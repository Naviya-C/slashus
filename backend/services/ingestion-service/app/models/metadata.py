from dataclasses import dataclass, field
from typing import Optional

@dataclass
class BlockMetadata:
    title: Optional[str] = None
    subtitle: Optional[str] = None
    sub_subtitles: list[str] = field(default_factory=list)
    page_number: int = 0
    block_index: int = 0
    block_type: str = "paragraph"
    font_size_hint: Optional[float] = None
    encoding_converted: bool = False
