"""
memory/conversation.py
======================

Per-session memory: history, summary, active topic, preferences.

WHY A SUMMARY AND NOT JUST HISTORY
----------------------------------
A twenty-turn session is thousands of tokens of Sinhala, and every decision
prompt would carry all of it. Worse, it carries it at the WRONG resolution:
the understanding node needs "we are discussing lesson 4, the student prefers
MCQs", not a verbatim replay of turn seven.

So two things are stored. The last few turns verbatim, because follow-up
resolution needs the actual words ("explain THAT" refers to something
specific). And a rolling summary that the LLM rewrites, because everything
older is only useful compressed.

WHY REDIS AND POSTGRES BOTH
---------------------------
Redis serves the hot path — this is read on every single turn. Postgres holds
the durable copy, so a cache eviction loses the summary (rebuildable) and not
the transcript (not rebuildable).

WHY PREFERENCES ARE LLM-WRITTEN AND NOT A SETTINGS FORM
-------------------------------------------------------
"Give me harder ones" and "shorter answers please" are preferences expressed
mid-conversation. A student will never open a settings panel to say that, so
if the agent cannot learn it from the conversation it will never know it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# How many turns go into a decision prompt verbatim. Six is three exchanges —
# enough for "explain that" -> "that" -> the thing before it, and short enough
# that the prompt stays cheap.
_VERBATIM_TURNS = 6

# Beyond this, older turns are folded into the summary rather than carried.
_SUMMARISE_AFTER = 12


@dataclass
class ConversationState:
    summary: str = ""
    active_topic: str = ""
    preferences: dict[str, Any] = field(default_factory=dict)
    recent_turns: list[dict[str, str]] = field(default_factory=list)
    turn_count: int = 0

    def is_empty(self) -> bool:
        return not self.recent_turns and not self.summary

    def as_prompt_block(self) -> str:
        """Rendered for a decision prompt.

        Returns a literal "(none)" rather than an empty string when there is
        no history. A blank region in a prompt reads to the model as a section
        it failed to receive, and it starts inventing plausible history to
        fill it — which then drives the routing decision.
        """
        if self.is_empty():
            return "(no previous conversation — this is the first turn)"

        parts = []
        if self.summary:
            parts.append(f"SUMMARY SO FAR: {self.summary}")
        if self.active_topic:
            parts.append(f"ACTIVE TOPIC: {self.active_topic}")
        if self.preferences:
            parts.append("PREFERENCES: " + ", ".join(
                f"{k}={v}" for k, v in self.preferences.items()))
        if self.recent_turns:
            parts.append("RECENT TURNS:")
            parts.extend(
                f"  {t['role']}: {t['content'][:300]}" for t in self.recent_turns)
        return "\n".join(parts)


class ConversationMemory:
    def __init__(self, scratch, repo=None) -> None:
        self._scratch = scratch
        self._repo = repo

    # ------------------------------------------------------------------

    def load(self, user_id: UUID, session_id: str) -> ConversationState:
        cached = self._scratch.get(user_id, session_id, "conversation")
        if cached:
            return ConversationState(**cached)

        # Cold cache. Rebuild the verbatim turns from Postgres; the summary is
        # lost and will be rebuilt on the next save. Losing a summary degrades
        # multi-turn reasoning for one turn — losing the transcript would be
        # unrecoverable, which is why only one of them lives in Redis alone.
        state = ConversationState()
        if self._repo is not None:
            try:
                page = self._repo.list_messages(user_id, UUID(session_id), limit=_VERBATIM_TURNS)
                state.recent_turns = [
                    {"role": m["role"], "content": m["content"]}
                    for m in reversed(page.get("messages", []))
                ]
                state.turn_count = len(state.recent_turns)
            except Exception:
                # A brand-new session_id that is not a UUID yet, or a DB
                # blip. Neither should stop the turn — an agent with no
                # memory still answers, it just cannot resolve follow-ups.
                logger.warning("conversation history unavailable", exc_info=True)

        return state

    # ------------------------------------------------------------------

    def save(self, user_id: UUID, session_id: str, state: ConversationState,
             user_message: str, assistant_message: str) -> None:
        state.recent_turns.append({"role": "user", "content": user_message})
        state.recent_turns.append({"role": "assistant", "content": assistant_message})
        state.turn_count += 1
        state.recent_turns = state.recent_turns[-_VERBATIM_TURNS:]

        self._scratch.set(user_id, session_id, "conversation", {
            "summary": state.summary,
            "active_topic": state.active_topic,
            "preferences": state.preferences,
            "recent_turns": state.recent_turns,
            "turn_count": state.turn_count,
        })

    @staticmethod
    def needs_summary(state: ConversationState) -> bool:
        return state.turn_count >= _SUMMARISE_AFTER and state.turn_count % 4 == 0
