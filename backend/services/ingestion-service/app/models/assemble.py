from dataclasses import dataclass

@dataclass
class Assemble:
    page_analysis: dict
    page_tables: list[dict]
    page_images: list[dict]
    page_number: int
    block_counter: list[int]
    heading_context: dict
    encoding_converted: bool