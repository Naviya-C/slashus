"""Regex routing rules (Sinhala + English + Singlish) and their priority."""

from __future__ import annotations

import re

from orchestrator.router.intents import Intent

RULES: list[tuple[Intent, re.Pattern]] = [
    (Intent.GENERATE_MORE, re.compile(
        r"\b(more|another|other|different|extra|additional|new)\b"
        r"|තව|තවත්|වෙනත්|අලුත්", re.IGNORECASE)),
    (Intent.GREETING, re.compile(
        r"^\s*(?:hi|hello|hey|good\s*(?:morning|afternoon|evening)|ayubowan)\b"
        r"|ආයුබෝවන්|ආයුබෝවන|හලෝ|හෙලෝ|සුබ\s*උදෑසන", re.IGNORECASE)),
    (Intent.MARK, re.compile(
        r"\b(mark|grade|evaluate\s+my|score\s+my|check\s+my\s+answers?)\b"
        r"|ලකුණු|ඇගයීම|පිළිතුරු\s*පරීක්ෂා", re.IGNORECASE)),
    (Intent.GENERATE, re.compile(
        r"\b(question|questions|mcq|quiz|exam|paper|summar\w+|flash\s*cards?|"
        r"flashcards?|explain|explanation|notes)\b"
        r"|ප්‍රශ්න|ප්\u200dරශ්න|විභාග|සාරාංශ|පැහැදිලි", re.IGNORECASE)),
    (Intent.RETRIEVE, re.compile(
        r"\b(find|search|show|what\s+is|tell\s+me\s+about|about)\b"
        r"|සොයන්න|ගැන|මොකක්ද|විස්තර", re.IGNORECASE)),
    (Intent.CASUAL, re.compile(
        r"\b(thanks|thank\s*you|ok|okay|bye|how\s+are\s+you)\b|ස්තූති|ස්තුති|හරි|බායි", re.IGNORECASE)),
]

# Action intents outrank a leading greeting/casual.
PRIORITY = [Intent.GENERATE_MORE, Intent.MARK, Intent.GENERATE, Intent.RETRIEVE, Intent.GREETING, Intent.CASUAL]
