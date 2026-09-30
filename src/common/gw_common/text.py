"""Text hygiene shared by every system, so the arms read the same corpus.

`looks_like_sentence` decides what counts as prose rather than page furniture (GRI index rows, table
fragments, headers). It started in the graph builder; it lives here because the baseline retriever
must apply the same filter, or the two arms would be reading different corpora and the RQ1
comparison would measure that instead of the retrieval strategy.
"""

from __future__ import annotations

import re

# Kept exactly as the graph builder had it: changing the wording would change which statements the
# graph already contains and break comparability with the runs recorded in the notes.
_WORDY = re.compile(
    r"\b(is|are|was|were|has|have|had|will|shall|can|may|we|our|the group|the company)\b", re.I
)
_TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = set(
    "the a an and or of to in for on with by at from as is are was were be been our we its their this "
    "that these those it has have had will shall can may also which who all any".split()
)


def looks_like_sentence(text: str) -> bool:
    """Coarse pre-filter for prose: 8-60 words, mostly letters, no URLs, not a shouty header."""
    words = text.split()
    if not 8 <= len(words) <= 60:
        return False
    chars = [c for c in text if not c.isspace()]
    letters = [c for c in chars if c.isalpha()]
    if not chars or len(letters) / len(chars) < 0.75:
        return False
    if sum(c.isdigit() for c in chars) / len(chars) > 0.10:
        return False
    if sum(c.isupper() for c in letters) / max(1, len(letters)) > 0.30:
        return False
    if re.search(r"https?:|www\.|\.{4,}|@", text):
        return False
    return bool(_WORDY.search(text))


def tokens(text: str, *, drop_stopwords: bool = True, min_len: int = 3) -> list[str]:
    """Lowercased alphanumeric tokens, the lexical unit BM25 and overlap scoring share."""
    out = _TOKEN.findall(text.lower())
    if drop_stopwords:
        out = [t for t in out if t not in STOPWORDS]
    return [t for t in out if len(t) >= min_len]
