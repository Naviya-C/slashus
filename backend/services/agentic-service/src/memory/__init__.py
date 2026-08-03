"""Memory: everything the agent knows that is not in the current message.

Five kinds, separated because they have genuinely different lifetimes and
failure modes — collapsing them into one store would mean the cheapest and
most volatile (working memory) forces the durability guarantees of the most
expensive (quiz history).

    working       one graph run          in-process, dies with the request
    conversation  one session            Redis + Postgres
    retrieval     one session            Redis
    quiz          forever                Postgres
    evaluation    forever                Postgres

WHY REDIS FOR TWO AND POSTGRES FOR TWO
--------------------------------------
Conversation and retrieval memory are read on EVERY turn and are worthless a
day later. Quiz and evaluation memory are read rarely and must survive a
Redis flush — a student's marks are not cache.

Conversation memory is written to both: Redis serves the hot path, Postgres
holds the durable copy so a cache eviction loses the summary, not the history.
"""

from memory.conversation import ConversationMemory, ConversationState
from memory.retrieval import RetrievalMemory, RetrievalSnapshot
from memory.store import MemoryStore, build_memory_store
from memory.working import WorkingMemory

__all__ = [
    "WorkingMemory",
    "ConversationMemory", "ConversationState",
    "RetrievalMemory", "RetrievalSnapshot",
    "MemoryStore", "build_memory_store",
]
