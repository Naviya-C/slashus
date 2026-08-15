"""
What may be cached, and what must always be answered live.

THE RULE
--------
A semantic cache keyed only on "how similar are these two sentences" produces
a robot. "Hi" and "Hello there" are ~0.95 similar, so a naive cache replays the
identical greeting forever and the tutor stops feeling like it is listening.

So similarity is the SECOND question. The first is whether this turn is the
kind of thing that has a reusable answer at all.

NEVER CACHED
------------
GREETINGS AND SMALL TALK. There is no correct answer to reuse -- the value is
in the response being fresh. These also cost one cheap model call and no tool
calls, so caching them saves almost nothing anyway.


CACHED
------
Substantive questions about document content, which is exactly where the money
goes: several tool calls, a large retrieval payload in context, and a long
generation. Those genuinely do have the same answer when asked the same thing
two different ways.
"""

from __future__ import annotations

import re
from enum import StrEnum


_GREETING_RE = re.compile(
    r"^\s*(?:"
    r"h(?:i|ey|ello|iya)|yo|sup|greetings|good\s+(?:morning|afternoon|evening|day)|"
    r"how\s+are\s+you|how'?s\s+it\s+going|what'?s\s+up|"
    r"thanks?|thank\s+you|ty|thx|ok(?:ay)?|cool|nice|great|bye|goodbye|see\s+you|"
    r"ආයුබෝවන්|හලෝ|හෙලෝ|සුබ\s*(?:උදෑසනක්|දවසක්|සන්ධ්‍යාවක්)|"
    r"ස්තූතියි|බොහොම\s*ස්තූතියි|හරි|හොඳයි|ගිහින්\s*එන්නම්"
    r")\s*[!.?]*\s*$",
    re.IGNORECASE,
)

_FOLLOWUP_RE = re.compile(
    r"(?:"
    r"\b(?:explain|tell)\s+(?:me\s+)?more\b|\bmore\s+detail|\bgo\s+on\b|\bcontinue\b|"
    r"\banother\s+(?:one|example)\b|\bnext\s+one\b|\bthe\s+(?:first|second|third|last)\s+one\b|"
    r"\bwhat\s+about\b|\band\s+then\b|\bwhy\s+is\s+that\b|\bwhat\s+do\s+you\s+mean\b|"
    r"\bsame\s+(?:thing|again)\b|\bagain\b|"
    r"තව\s*විස්තර|තවත්|දිගටම|ඊළඟ|තව\s*උදාහරණ|ඒක\s*මොකද|නැවත"
    r")",
    re.IGNORECASE,
)


_PERSONAL_RE = re.compile(
    r"(?:"
    r"\bwhat\s+(?:am|was)\s+i\b|\bwhat\s+did\s+i\b|\bmy\s+(?:progress|score|marks|results|goal)\b|"
    r"\bdo\s+you\s+remember\b|\blast\s+time\b|\bearlier\b|\bwe\s+discussed\b|"
    r"මම\s*මොනවද|මගේ\s*(?:ලකුණු|ප්‍රගතිය)|ඔයාට\s*මතකද|පසුගිය"
    r")",
    re.IGNORECASE,
)

SIDE_EFFECT_TOOLS = frozenset(
    {
        "save_practice_questions",
        "evaluate_practice_answer",
        "remember_about_student",
        "learn_tutoring_rule",
    }
)

MIN_CACHEABLE_CHARS = 12


class CacheDecision(StrEnum):
    CACHEABLE = "cacheable"
    GREETING = "greeting"
    FOLLOWUP = "followup"
    PERSONAL = "personal"
    TOO_SHORT = "too_short"
    SIDE_EFFECTS = "side_effects"
    EMPTY_ANSWER = "empty_answer"
    HAS_HISTORY = "has_history"


def is_greeting(message: str) -> bool:
    return bool(_GREETING_RE.match(message.strip()))


def classify_request(message: str, *, has_history: bool = False) -> CacheDecision:
    """Decide whether this turn may be SERVED from cache."""
    text = message.strip()

    if is_greeting(text):
        return CacheDecision.GREETING
    if _PERSONAL_RE.search(text):
        return CacheDecision.PERSONAL
    if has_history and _FOLLOWUP_RE.search(text):
        return CacheDecision.FOLLOWUP
    if has_history:
        return CacheDecision.HAS_HISTORY
    if len(text) < MIN_CACHEABLE_CHARS:
        return CacheDecision.TOO_SHORT

    return CacheDecision.CACHEABLE


def classify_response(
    *, answer: str, tools_used: list[str], timed_out: bool = False
) -> CacheDecision:
    """
    Decide whether this turn's ANSWER may be STORED.

    Separate from the request check because some disqualifiers are only visible
    after the fact which tools ran, whether an answer was produced at all.
    """
    if timed_out or not answer.strip():
        return CacheDecision.EMPTY_ANSWER
    if any(tool in SIDE_EFFECT_TOOLS for tool in tools_used):
        return CacheDecision.SIDE_EFFECTS
    return CacheDecision.CACHEABLE
