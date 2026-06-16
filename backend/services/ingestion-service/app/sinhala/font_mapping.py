import re

LEGACY_FONT_PATTERNS = [
    r"fm[\.\-_]?abhaya",
    r"fm[\.\-_]?malithi",
    r"fm[\.\-_]?gemunu",
    r"fm[\.\-_]?bindumathi",
    r"fm[\.\-_]?yazida",
    r"fm[\.\-_]?gangani",
    r"fm[\.\-_]?champa",
    r"fm[\.\-_]?suwaya",
    r"fm[\.\-_]?sunil",
    r"fm[\.\-_]?ridi",
    r"fm[\.\-_]?paras",
    r"fm[\.\-_]?nirmali",
    r"fm[\.\-_]?kaputa",
    r"fm[\.\-_]?arjuna",
    r"wijeya",
    r"dinamina",
    r"iskoola[\.\-_]?pota",
]

FONT_TO_MAPPING: dict[str, str] = {
    "fm_abhaya":     "fm_abhaya",
    "fm_malithi":    "fm_abhaya",
    "fm_gemunu":     "fm_abhaya",
    "fm_bindumathi": "fm_abhaya",
    "wijeya":        "fm_abhaya",
    "dinamina":      "fm_abhaya",
}


def _normalise_font_name(name: str) -> str:
    return name.lower().replace(" ", ".").replace("-", ".").replace("_", ".")

def _resolve_mapping(normalised_font_name: str) -> str:
    for key in FONT_TO_MAPPING:
        if key.replace("_", ".") in normalised_font_name:
            return FONT_TO_MAPPING[key]
    return "fm_abhaya"


def has_sinhala_unicode(text: str) -> bool:
    return bool(re.search(r"[\u0d80-\u0dff]", text))


def looks_like_legacy_ascii_sinhala(text: str) -> bool:
    if has_sinhala_unicode(text):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    special = len(re.findall(r'[%\$\#\@\!\*\+\=\^\&\;\:\,\<\>\?\/\\\|\~\`\'\"]', stripped))
    return (special / len(stripped)) > 0.08