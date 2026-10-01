"""Page cleaning and sentence splitting.

Ported verbatim in behaviour from the annotation sampling pipeline
(`kb/annotation/work/build_reserve.py`) so that a statement parsed here is character-identical to the
sentence that was annotated. If this file and the annotation splitter ever disagree, the graph loses
its join to the eval set, so changes here must be mirrored there.
"""

from __future__ import annotations

import re

ABBR = [
    "e.g.", "i.e.", "etc.", "No.", "no.", "Mr.", "Ms.", "Mrs.", "Dr.", "Ltd.", "Pte.", "Co.", "Inc.",
    "approx.", "vs.", "Fig.", "Jan.", "Feb.", "Mar.", "Apr.", "Jun.", "Jul.", "Aug.", "Sep.", "Sept.",
    "Oct.", "Nov.", "Dec.", "St.", "Bhd.", "Corp.", "Dept.", "U.S.", "S.E.A.",
]
_SENT_SPLIT = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"”’)]))\s+(?=[A-Z“\"‘(])")
_DESPACE = re.compile(r"\b(?:\w ){2,}\w\b")
_DETERMINERS = re.compile(r"^(the|our|its|their|a|an|this|these|those|his|her)\s+", re.I)


def despace(text: str) -> str:
    """Cover pages often letter-space titles ('S U S T A I N A B I L I T Y')."""
    return _DESPACE.sub(lambda m: m.group(0).replace(" ", ""), text)


def clean_page(text: str) -> str:
    t = text.replace("­", "").replace("‑", "-")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    t = re.sub(r"[•●▪■]", " ", t)
    t = re.sub(r"\s*\n\s*", " ", t)
    return despace(re.sub(r"\s+", " ", t)).strip()


def split_sentences(text: str) -> list[str]:
    t = text
    for i, abbr in enumerate(ABBR):
        t = t.replace(abbr, abbr.replace(".", f"<DOT{i}>"))
    parts = _SENT_SPLIT.split(t)
    return [re.sub(r"<DOT\d+>", ".", p).strip() for p in parts if p.strip()]


def normalise(text: str) -> str:
    """Loose key for matching sentences and aspect surface forms."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def aspect_key(surface: str) -> str:
    """M1 aspect identity: normalised text with a leading determiner or possessive removed.

    Deliberately conservative — two surface forms merge only if they are the same words. Embedding
    clustering is M2 and is gated on a purity audit before it may create merges.
    """
    return _DETERMINERS.sub("", normalise(surface)).strip()
