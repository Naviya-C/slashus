"""Session, message and practice-set persistence.

The Supabase history store and the in-memory session store are gone: all
state now lives in Postgres via Repository, and the scratch space used for
"give me more" is Redis. One store per concern, both already running in the
compose stack.
"""

from state.repository import Repository
from state.scratch import Scratch, build_scratch

__all__ = ["Repository", "Scratch", "build_scratch"]
