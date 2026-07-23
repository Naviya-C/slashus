"""Intent enum and intent -> ordered agent-steps mapping.

INTENT_STEPS declares multi-agent sequencing. Add a new agent's route here;
the graph reads these steps blindly.
"""

from __future__ import annotations

from enum import Enum 


class Intent(str, Enum):
    GREETING = "greeting"
    CASUAL = "casual"
    RETRIEVE = "retrieve"
    GENERATE = "generate"          # questions/summary/flashcards/explanation
    GENERATE_MORE = "generate_more"  # "give me more/different ones" — continues
    MARK = "mark"                  # grade student answers


INTENT_STEPS: dict[Intent, list[str]] = {
   # maps each intent to the ordered list of agent names to run
    Intent.GREETING: [],                              # pure node
    Intent.CASUAL: [],                                # pure node
    Intent.RETRIEVE: ["retrieve"],
    Intent.GENERATE: ["retrieve", "generate"],        # retrieve → generate (chained)
    # "more" reuses the chunks/artifact already in session — skips retrieval,
    # generates NEW items that avoid what was already shown.
    Intent.GENERATE_MORE: ["generate"],
    Intent.MARK: ["mark"],                            # grades a submission
}
