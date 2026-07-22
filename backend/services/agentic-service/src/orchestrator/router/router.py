"""Hybrid router: rules first (free), LLM fallback for ambiguous prompts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from core.llm import LLMClient
from orchestrator.router.intents import INTENT_STEPS, Intent
from orchestrator.router.rules import PRIORITY, RULES

logger = logging.getLogger(__name__)

_LLM_PROMPT = (
    "Classify this study-assistant message into ONE intent.\nMESSAGE: {msg}\n"
    "Options: greeting, casual, retrieve, generate_questions, mark.\n"
    "Reply with ONLY one word."
)
 

@dataclass(slots = True)
class Route:
    intent: Intent
    method: str
    steps: list[str] = field(default_factory = list)


class Router:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm

    def route(self, message: str) -> Route:
        matched = {i for i, p in RULES if p.search(message)}
        for intent in PRIORITY:
            if intent in matched:
                return Route(intent, "rules", INTENT_STEPS[intent])

        if self._llm is not None:
            try:
                w = self._llm.generate(_LLM_PROMPT.format(msg = message)).strip().lower()
                intent = next((i for i in Intent if i.value in w), Intent.RETRIEVE)
            except Exception:
                logger.warning("LLM routing failed; default retrieve")
                intent = Intent.RETRIEVE
            return Route(intent, "llm", INTENT_STEPS[intent])

        return Route(Intent.RETRIEVE, "default", INTENT_STEPS[Intent.RETRIEVE])
