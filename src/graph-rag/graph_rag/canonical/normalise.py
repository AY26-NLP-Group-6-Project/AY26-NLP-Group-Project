"""Morphological normalisation of aspect surface forms (the canonicalisation baseline).

This is the "Morph Norm" family from the canonicalisation literature (CESI, WWW 2018, section 7.3:
"removing tense, pluralization, capitalization etc."). CESI's own results are the reason it is only a
baseline: on ReVerb45K it reaches micro F1 77.7 but macro F1 1.4, i.e. it almost never merges the
clusters that matter. It still runs first, because every later stage is cheaper on deduplicated keys.
"""

from __future__ import annotations

import re

# ESG acronyms that appear as standalone tokens. Expansion only, never contraction, and only for
# acronyms whose expansion is unambiguous inside sustainability reports.
ABBREVIATIONS: dict[str, str] = {
    "ghg": "greenhouse gas",
    "ghgs": "greenhouse gas",
    "ohs": "occupational health and safety",
    "wsh": "workplace safety and health",
    "hse": "health safety and environment",
    "qhse": "quality health safety and environment",
    "pdpa": "personal data protection act",
    "kpi": "key performance indicator",
    "kpis": "key performance indicator",
    "csr": "corporate social responsibility",
    "tcfd": "task force on climate related financial disclosures",
    "sbti": "science based targets initiative",
    "recs": "renewable energy certificate",
    "rec": "renewable energy certificate",
    "ev": "electric vehicle",
    "evs": "electric vehicle",
    "erm": "enterprise risk management",
    "dei": "diversity equity and inclusion",
    "sdgs": "sustainable development goal",
    "sdg": "sustainable development goal",
    "unsdgs": "sustainable development goal",
}

_LEADING = re.compile(
    r"^(?:(?:the|our|its|their|a|an|this|these|those|all|any|such|his|her|group|company)\s+)+"
)
_PAREN_ACRONYM = re.compile(r"\s*\(([A-Za-z&]{2,8}s?)\)")
# acronyms written with an ampersand must be read before '&' becomes 'and'
_AMPERSAND_ACRONYMS = [
    (re.compile(r"\boh\s*&\s*s\b"), "ohs"),
    (re.compile(r"\bd\s*&\s*i\b"), "diversity and inclusion"),
]
_KEEP_S = ("ss", "us", "is", "ics", "sis", "ous", "ess")


def _singularise(word: str) -> str:
    if len(word) <= 3 or word.endswith(_KEEP_S):
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("sses", "xes", "ches", "shes")):
        return word[:-2]
    if word.endswith("s"):
        return word[:-1]
    return word


def morph_key(surface: str) -> str:
    """Lowercase, drop bracketed acronyms, expand known acronyms, strip leading determiners and
    company references, unify '&' and hyphens, singularise the head (last) token."""
    text = _PAREN_ACRONYM.sub("", surface).lower()
    for pattern, replacement in _AMPERSAND_ACRONYMS:
        text = pattern.sub(replacement, text)
    text = text.replace("&", " and ").replace("’", "'")
    text = re.sub(r"'s\b", "", text)
    text = re.sub(r"[-/]", " ", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    expanded: list[str] = []
    for token in text.split():
        expanded.extend(ABBREVIATIONS.get(token, token).split())
    text = _LEADING.sub("", " ".join(expanded)).strip()
    if not text:
        return ""
    words = text.split()
    words[-1] = _singularise(words[-1])
    return " ".join(words)
