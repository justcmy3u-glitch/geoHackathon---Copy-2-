# -*- coding: utf-8 -*-
"""
local_normalizer.py
Regex-based geological NER and text normalisation.

Public API
----------
LocalNormalizer().normalize(text) -> {"text": str, "entities": list, "needs_llm": bool}
LocalNormalizer().extract_entities(text) -> (normalised_text, entity_list)
LocalNormalizer().needs_llm(text, entities) -> bool
"""

import re
from typing import List, Tuple, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Unicode digit maps (subscript / superscript → ASCII)
# ---------------------------------------------------------------------------
_SUBSCRIPT_MAP = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUPERSCRIPT_MAP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def _norm_digits(text: str) -> str:
    return text.translate(_SUBSCRIPT_MAP).translate(_SUPERSCRIPT_MAP)


# ---------------------------------------------------------------------------
# Named-formation synonyms: map to canonical codes
# Used for NAMED formations (bazhenovskaya → BZH) that don't have digit suffixes.
# Keys are lower-cased; lookup is case-insensitive.
# ---------------------------------------------------------------------------
_NAMED_FORMATIONS: Dict[str, str] = {
    "баженовская свита":    "БЖ",
    "баженовская":          "БЖ",
    "тюменская свита":      "ТМ",
    "тюменская":            "ТМ",
    "ачимовская толща":     "АЧ",
    "ачимовская":           "АЧ",
    "васюганская свита":    "ВС",
    "васюганская":          "ВС",
    "абалакская свита":     "АБ",
    "абалакская":           "АБ",
}
# Sort longest-first to prevent partial overlaps
_NAMED_FORMATIONS_SORTED = sorted(_NAMED_FORMATIONS.items(), key=lambda kv: -len(kv[0]))

# ---------------------------------------------------------------------------
# Index-code synonyms: Ju1-3 → Ю1-3 etc.
# Applied BEFORE regex matching (after unicode normalisation).
# ---------------------------------------------------------------------------
_INDEX_SYNONYMS: List[Tuple[str, str]] = sorted([
    ("Ju1-3",  "Ю1-3"),
    ("ju1_3",  "Ю1-3"),
    ("Ю1_3",   "Ю1-3"),
    ("Ю₁³",    "Ю1-3"),
    ("Ю1³",    "Ю1-3"),
    ("БС¹⁰",   "БС10"),
    ("бс¹⁰",   "БС10"),
    ("bc10",   "БС10"),
    ("BC10",   "БС10"),
    ("bc-10",  "БС10"),
], key=lambda kv: -len(kv[0]))


def _apply_index_synonyms(text: str) -> str:
    """Case-insensitive replacement of index-code aliases."""
    for key, value in _INDEX_SYNONYMS:
        text = re.sub(re.escape(key), value, text, flags=re.IGNORECASE)
    return text


def _apply_named_formations(text: str) -> str:
    """Replace named formations with canonical codes, case-insensitive."""
    for key, value in _NAMED_FORMATIONS_SORTED:
        text = re.sub(re.escape(key), value, text, flags=re.IGNORECASE)
    return text


# ---------------------------------------------------------------------------
# Regex patterns — (compiled_pattern, replacement_callable)
# Applied on text that has already been unicode-normalised and synonym-replaced.
# ---------------------------------------------------------------------------

def _formation_repl(m: re.Match) -> str:
    """горизонт/пласт/свита <INDEX> → ПЛАСТ_<canonical>"""
    label = _norm_digits(m.group(1).strip())
    # Ensure dash separator: Ю13 → Ю1-3, БС10 stays as is
    label = re.sub(
        r'^([А-ЯЁA-Z]{1,4})(\d+)-?(\d+)$',
        lambda mm: f"{mm.group(1)}{mm.group(2)}-{mm.group(3)}" if mm.group(3) else f"{mm.group(1)}{mm.group(2)}",
        label,
        flags=re.IGNORECASE,
    )
    return f"ПЛАСТ_{label}"


def _depth_repl(m: re.Match) -> str:
    val = m.group(1).replace(",", ".")
    return f"ГЛУБИНА_{val}м"


# Formation pattern: "пласт Ю1-3", "горизонт БС10", also bare canonical codes БЖ/ТМ etc.
_PAT_FORMATION = re.compile(
    r'(?:горизонт|пласт|свита|толща|горизонте|пласте)\s+'
    r'([А-ЯЁа-яёA-Za-z]{1,4}[\d\-]+)',
    re.IGNORECASE | re.UNICODE,
)
# Stand-alone canonical code left by synonym replacement (e.g. БЖ, ТМ, АЧ)
_PAT_CANONICAL_CODE = re.compile(
    r'\b(БЖ|ТМ|АЧ|ВС|АБ)\b',
    re.UNICODE,
)
# Standalone formation index (e.g. Ю1-3, БС10, БВ8) — appears without prefix
# after synonym normalisation (Ju1-3 → Ю1-3, БС¹⁰ → БС10)
_PAT_BARE_INDEX = re.compile(
    r'\b([А-ЯЁA-Z]{1,4}\d+(?:-\d+)?)\b',
    re.UNICODE,
)
# Well number
_PAT_WELL = re.compile(
    r'скваж[а-яёА-ЯЁ]{0,3}\.?\s*[№#]?\s*(\d{1,5}[а-яА-Я]?)',
    re.IGNORECASE | re.UNICODE,
)
# Depth value
_PAT_DEPTH = re.compile(
    r'(\d{3,5}[,\.]\d{0,2})\s*м\.?\s*(?:кровл[яи]|подошв[аы]|глубин[аы]?)?',
    re.IGNORECASE | re.UNICODE,
)
# Oil saturation
_PAT_KN = re.compile(r'[Кк]н\s*=\s*(0\.\d+)', re.UNICODE)
# Porosity
_PAT_KP = re.compile(r'[Кк]п\s*=\s*(0\.\d+)', re.UNICODE)
# Coordinates
_PAT_COORD = re.compile(
    r'(\d{2}°\d{2}[\'′]\d{0,2}[″"]?)\s*[сСнН]\.?\s*[шШ]',
    re.UNICODE,
)

PATTERNS: List[Tuple[re.Pattern, Any]] = [
    (_PAT_FORMATION,      _formation_repl),
    (_PAT_CANONICAL_CODE, lambda m: f"ПЛАСТ_{m.group(1)}"),
    (_PAT_BARE_INDEX,     lambda m: f"ПЛАСТ_{m.group(1)}"),
    (_PAT_WELL,           lambda m: f"СКВАЖИНА_{m.group(1)}"),
    (_PAT_DEPTH,          _depth_repl),
    (_PAT_KN,             lambda m: f"НЕФТЕНАСЫЩЕННОСТЬ_{m.group(1)}"),
    (_PAT_KP,             lambda m: f"ПОРИСТОСТЬ_{m.group(1)}"),
    (_PAT_COORD,          lambda m: f"КООРДИНАТА_{m.group(1)}"),
]


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def apply_synonyms(text: str) -> str:
    """Full pre-processing pipeline: unicode normalise → index synonyms → named formations."""
    text = _norm_digits(text)
    text = _apply_index_synonyms(text)
    text = _apply_named_formations(text)
    return text


def extract_entities(text: str) -> Tuple[str, List[str]]:
    """
    Apply synonym pre-processing then run all regex patterns.
    Returns (normalised_text, list_of_entity_tokens).
    """
    normalised = apply_synonyms(text)
    found: List[str] = []

    for pattern, repl in PATTERNS:
        for match in pattern.finditer(normalised):
            val = repl(match)
            if val not in found:   # deduplicate
                found.append(val)

    return normalised, found


def needs_llm(text: str, entities_found: List[str]) -> bool:
    """
    Returns True when regex coverage is very low — meaning the chunk likely
    contains complex or ambiguous geological terminology that warrants LLM NER.

    Logic:
    - Count 'meaningful' words (≥ 4 chars) in text.
    - If entities_found is empty AND text has ≥ 10 meaningful words → needs LLM.
    - Otherwise True if coverage ratio < 0.04 (< 4 entities per 100 words).
    """
    words = [w for w in text.split() if len(w) >= 4]
    if not words:
        return False
    if not entities_found and len(words) >= 10:
        return True
    coverage = len(entities_found) / len(words)
    return coverage < 0.04 and len(words) >= 10


def normalize(text: str) -> Dict[str, Any]:
    """
    Main entry point.
    Returns: {"text": <normalised>, "entities": [...], "needs_llm": bool}
    """
    normalised, entities = extract_entities(text)
    return {
        "text":      normalised,
        "entities":  entities,
        "needs_llm": needs_llm(text, entities),
    }


# ---------------------------------------------------------------------------
# OOP wrapper
# ---------------------------------------------------------------------------

class LocalNormalizer:
    """Object-oriented wrapper — used as: LocalNormalizer().normalize(text)"""

    def normalize(self, text: str) -> Dict[str, Any]:
        return normalize(text)

    def extract_entities(self, text: str) -> Tuple[str, List[str]]:
        return extract_entities(text)

    def needs_llm(self, text: str, entities_found: Optional[List[str]] = None) -> bool:
        if entities_found is None:
            _, entities_found = extract_entities(text)
        return needs_llm(text, entities_found)
