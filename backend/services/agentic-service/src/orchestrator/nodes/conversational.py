"""Pure conversational nodes — greeting & casual. No agent, no LLM."""

from __future__ import annotations

from core.embedding import detect_language


def greeting_node(message: str) -> str:
    if detect_language(message) == "si":
        return "ආයුබෝවන්! පාඩම් වලට අදාළ ප්‍රශ්න, පිළිතුරු හෝ තොරතුරු අවශ්‍ය නම් කියන්න."
    return "Hello! I can find lesson content and generate questions. What would you like?"


def casual_node(message: str) -> str:
    if detect_language(message) == "si":
        return "සතුටුයි! තවත් යමක් අවශ්‍ය නම් අසන්න."
    return "You're welcome! Ask me anything about your lessons."
