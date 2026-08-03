"""Intent router — one LLM call per message."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from orchestrator.router.intents import INTENT_STEPS, Intent
from prompts import pool

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Route:
    intent: Intent
    method: str
    steps: list[str] = field(default_factory=list)
    confidence: float = 0.0


class Router:
    def __init__(self, llm=None) -> None:
        self._llm = llm

    def route(self, message: str) -> Route:
        if self._llm is None:
            logger.warning("no LLM configured; defaulting to generate")
            return Route(Intent.GENERATE, "default", INTENT_STEPS[Intent.GENERATE])

        try:
            data = self._llm.generate_json(
                pool.render("INTENT", user_query=message), temperature=0.0
            )
            raw = str(data.get("intent", "")).strip().lower()
            chosen = next(
                (i for i in sorted(Intent, key=lambda x: -len(x.value))
                 if i.value in raw),
                Intent.GENERATE,
            )
            logger.info("route: %s (llm)", chosen.value)
            return Route(chosen, "llm", INTENT_STEPS[chosen])

        except Exception:
            logger.warning("LLM routing failed; defaulting to generate", exc_info=True)
            return Route(Intent.GENERATE, "default", INTENT_STEPS[Intent.GENERATE])