"""Query understanding: normalize + detect language + extract metadata."""

from __future__ import annotations

import logging
from string import Template

from core.embedding import detect_language
from core.llm import QwenClient, LLMClient
from agents.retrieval.schemas import Understanding

logger = logging.getLogger(__name__)

_PROMPT = Template(
    """Analyze this educational query. Normalize to standard form.

QUERY: $query

Return ONLY JSON:
{"normalized_query": "...", "question_count": 1, "complexity": "simple",
 "metadata": {"lesson_no": null, "page_number": null, "lesson_title": null, "source_file": null}}
"""
)


class QueryUnderstanding:
    def __init__(self, llm: LLMClient | QwenClient) -> None:
        self._llm = llm

    def understand(self, query: str) -> Understanding:
        language = detect_language(query)
        try:
            data = self._llm.generate_json(_PROMPT.substitute(query=query))
        except RuntimeError:
            logger.warning("Understanding failed; fallback")
            return Understanding(query, query, language=language)
        meta = {k: v for k, v in (data.get("metadata") or {}).items() if v is not None}
        return Understanding(
            raw_query=query,
            normalized_query=str(data.get("normalized_query") or query),
            language=language,
            question_count=max(1, int(data.get("question_count") or 1)),
            complexity=str(data.get("complexity", "simple")),
            metadata=meta,
        )
