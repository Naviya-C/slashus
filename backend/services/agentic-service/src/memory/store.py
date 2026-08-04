"""
memory/store.py
===============

One facade over every kind of memory, so the graph has two memory nodes
(`load_memory`, `save_memory`) instead of five scattered calls.

Quiz and evaluation memory are not separate classes here: they are the
Repository, which already stores practice sets, questions and marked answers
with the right ownership scoping. Wrapping it in a MemoryStore-flavoured shim
would add a layer that only forwards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from memory.conversation import ConversationMemory, ConversationState
from memory.retrieval import RetrievalMemory, RetrievalSnapshot

logger = logging.getLogger(__name__)


@dataclass
class LoadedMemory:
    conversation: ConversationState
    retrieval: RetrievalSnapshot


class MemoryStore:
    def __init__(self, conversation: ConversationMemory,
                 retrieval: RetrievalMemory, repo=None) -> None:
        self.conversation = conversation
        self.retrieval = retrieval
        self.repo = repo

    def load(self, user_id: UUID, session_id: str) -> LoadedMemory:
        return LoadedMemory(
            conversation=self.conversation.load(user_id, session_id),
            retrieval=self.retrieval.load(user_id, session_id),
        )

    def save_retrieval(self, user_id: UUID, session_id: str,
                       snapshot: RetrievalSnapshot) -> None:
        try:
            self.retrieval.save(user_id, session_id, snapshot)
        except Exception:
            # Memory is an optimisation. Failing to write it must never fail
            # a turn that already produced a good answer.
            logger.warning("retrieval memory write failed", exc_info=True)

    def save_conversation(self, user_id: UUID, session_id: str,
                          state: ConversationState, user_message: str,
                          assistant_message: str) -> None:
        try:
            self.conversation.save(user_id, session_id, state,
                                   user_message, assistant_message)
        except Exception:
            logger.warning("conversation memory write failed", exc_info=True)


def build_memory_store(scratch, repo=None) -> MemoryStore:
    return MemoryStore(
        conversation=ConversationMemory(scratch, repo),
        retrieval=RetrievalMemory(scratch),
        repo=repo,
    )
