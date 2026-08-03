"""Intent enum and intent -> ordered agent-steps mapping.

INTENT_STEPS declares multi-agent sequencing. Add a new agent's route here;
the graph reads these steps blindly.

There is no RETRIEVE intent. Retrieval is a STEP, not something a user asks
for — and an intent named after it produced a route that returned raw chunks
with no synthesis, which is a debugging view rather than an answer. Questions
about the material go through GENERATE, whose artifact detection decides
between a practice set and a written answer.
"""

from __future__ import annotations

from enum import Enum


class Intent(str, Enum):
    GREETING = "greeting"
    CASUAL = "casual"
    GENERATE = "generate"            # questions, answers, summaries, flashcards
    GENERATE_MORE = "generate_more"  # "give me more" — continues the last set
    MARK = "mark"                    # grade student answers


INTENT_STEPS: dict[Intent, list[str]] = {
    Intent.GREETING: [],                        # pure node, no agents
    Intent.CASUAL: [],                          # pure node, no agents
    Intent.GENERATE: ["retrieve", "generate"],
    # Reuses chunks already in the session; skips retrieval and generates new
    # items that avoid what was already shown.
    Intent.GENERATE_MORE: ["generate"],
    Intent.MARK: ["mark"],
}
