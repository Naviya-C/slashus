from __future__ import annotations

import re
from collections.abc import Iterable

from ingestion_service.domain import BlockType, Chunk, ExtractedBlock


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+|\n{2,}")


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    words = len(text.split())
    non_ascii = sum(1 for character in text if ord(character) > 127)
    return max(1, int(words * 1.35 + non_ascii / 4))


class BlockChunker:
    def __init__(self, *, max_tokens: int, overlap_tokens: int) -> None:
        self._max = max_tokens
        self._overlap = min(overlap_tokens, max_tokens // 3)

    def chunks(
        self,
        blocks: Iterable[ExtractedBlock],
        *,
        page: int | None,
        start_index: int,
    ) -> list[Chunk]:
        output: list[Chunk] = []
        buffer: list[ExtractedBlock] = []
        buffer_tokens = 0

        def flush() -> None:
            nonlocal buffer, buffer_tokens
            if not buffer:
                return
            text = "\n\n".join(item.text.strip() for item in buffer if item.text.strip()).strip()
            if text:
                primary = buffer[0]
                output.append(
                    Chunk(
                        text=text,
                        embed_text=_embedding_text(primary.section_path, text),
                        type=_combined_type(buffer),
                        section_path=list(primary.section_path),
                        page=page,
                        bbox=primary.bbox if len(buffer) == 1 else None,
                        chunk_index=start_index + len(output),
                        token_count=estimate_tokens(text),
                        extra={"unit": page},
                    )
                )
            overlap = _tail_blocks(buffer, self._overlap)
            buffer = overlap
            buffer_tokens = sum(estimate_tokens(item.text) for item in overlap)

        for block in blocks:
            text = block.text.strip()
            if not text:
                continue
            if block.block_type in {BlockType.TABLE, BlockType.IMAGE}:
                flush()
                for piece in self._split(text):
                    output.append(
                        Chunk(
                            text=piece,
                            embed_text=_embedding_text(block.section_path, piece),
                            type=block.block_type,
                            section_path=list(block.section_path),
                            page=page,
                            bbox=block.bbox,
                            chunk_index=start_index + len(output),
                            token_count=estimate_tokens(piece),
                            extra={**block.metadata, "unit": page},
                        )
                    )
                continue
            tokens = estimate_tokens(text)
            if tokens > self._max:
                flush()
                for piece in self._split(text):
                    output.append(
                        Chunk(
                            text=piece,
                            embed_text=_embedding_text(block.section_path, piece),
                            type=block.block_type,
                            section_path=list(block.section_path),
                            page=page,
                            bbox=block.bbox,
                            chunk_index=start_index + len(output),
                            token_count=estimate_tokens(piece),
                            extra={**block.metadata, "unit": page},
                        )
                    )
                continue
            if buffer and buffer_tokens + tokens > self._max:
                flush()
            buffer.append(block)
            buffer_tokens += tokens
        flush()
        return output

    def _split(self, text: str) -> list[str]:
        if estimate_tokens(text) <= self._max:
            return [text]
        sentences = [part.strip() for part in _SENTENCE_BOUNDARY.split(text) if part.strip()]
        if len(sentences) == 1:
            return _word_chunks(text, self._max, self._overlap)
        expanded: list[str] = []
        for sentence in sentences:
            if estimate_tokens(sentence) > self._max:
                expanded.extend(_word_chunks(sentence, self._max, self._overlap))
            else:
                expanded.append(sentence)
        sentences = expanded
        pieces: list[str] = []
        current: list[str] = []
        current_tokens = 0
        for sentence in sentences:
            tokens = estimate_tokens(sentence)
            if current and current_tokens + tokens > self._max:
                pieces.append(" ".join(current))
                current = _sentence_tail(current, self._overlap)
                current_tokens = estimate_tokens(" ".join(current))
            current.append(sentence)
            current_tokens += tokens
        if current:
            pieces.append(" ".join(current))
        return pieces


def _combined_type(blocks: list[ExtractedBlock]) -> BlockType:
    types = {block.block_type for block in blocks}
    return next(iter(types)) if len(types) == 1 else BlockType.TEXT


def _embedding_text(section_path: list[str], text: str) -> str:
    prefix = " > ".join(section_path)
    return f"{prefix}\n{text}" if prefix else text


def _tail_blocks(blocks: list[ExtractedBlock], token_budget: int) -> list[ExtractedBlock]:
    if token_budget <= 0:
        return []
    selected: list[ExtractedBlock] = []
    used = 0
    for block in reversed(blocks):
        tokens = estimate_tokens(block.text)
        if used + tokens > token_budget:
            break
        selected.append(block)
        used += tokens
    return list(reversed(selected))


def _sentence_tail(sentences: list[str], token_budget: int) -> list[str]:
    selected: list[str] = []
    used = 0
    for sentence in reversed(sentences):
        tokens = estimate_tokens(sentence)
        if used + tokens > token_budget:
            break
        selected.append(sentence)
        used += tokens
    return list(reversed(selected))


def _word_chunks(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    output: list[str] = []
    start = 0
    while start < len(words):
        end = start
        while end < len(words):
            candidate = " ".join(words[start : end + 1])
            if end > start and estimate_tokens(candidate) > max_tokens:
                break
            end += 1
        if end == start:
            end += 1
        output.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        overlap_start = end
        while overlap_start > start:
            candidate = " ".join(words[overlap_start - 1 : end])
            if estimate_tokens(candidate) > overlap_tokens:
                break
            overlap_start -= 1
        start = overlap_start if overlap_start < end else end
    return output
