from dataclasses import dataclass

from app.models.metadata import BlockMetadata

@dataclass
class Block:
    block_type: str
    content: str | list | dict
    metadata: BlockMetadata