"""
src/prompts/pool.py
===================

Loads prompt templates from .md files and substitutes {{variables}}.

Why files rather than string constants in Python:

  * The same LLM serves intent, generation, marking and answering. Each needs
    a genuinely different prompt, and keeping them in one .py turns that file
    into a wall of triple-quoted strings nobody wants to edit.
  * Prompt changes become reviewable diffs about wording, not code changes.
  * A non-programmer can improve a rubric or fix Sinhala phrasing without
    touching Python.

Templates are cached after first read: they never change at runtime, and this
avoids a disk hit on every request.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent
_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


@lru_cache(maxsize=32)
def _load(name: str) -> str:
    path = _PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def render(name: str, **values: Any) -> str:
    """Render `name`.md with the given values.

    Deliberately NOT str.format or Template: prompt files are full of literal
    braces (JSON examples), and both of those choke on them. A regex over an
    explicit {{var}} syntax leaves JSON braces alone.

    Missing variables raise rather than silently rendering "{{sources}}" into
    the prompt — which produces an LLM response that looks plausible and is
    based on nothing.
    """
    template = _load(name)
    missing = set(_VAR_RE.findall(template)) - set(values)
    if missing:
        raise KeyError(f"{name}.md missing variables: {sorted(missing)}")

    def sub(m: re.Match) -> str:
        return str(values[m.group(1)])

    return _VAR_RE.sub(sub, template)


def available() -> list[str]:
    """Template names on disk. Useful in a startup log to catch a missing
    file before the first request rather than at 3am."""
    return sorted(p.stem for p in _PROMPT_DIR.glob("*.md"))
