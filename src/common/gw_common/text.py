"""Text conventions shared by every system, so the arms read the same corpus.

The knowledge base is every statement of the parsed reports with at least `MIN_STATEMENT_WORDS` words:
prose, table rows and metric lines alike. Shorter fragments are headers, page numbers and lone table
cells. `is_statement` is that one rule; the baseline chunker and the graph's lexical fallback both
apply it, so the two arms retrieve over the same set.
"""

from __future__ import annotations

import re

MIN_STATEMENT_WORDS = 5

_TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = set(
    "the a an and or of to in for on with by at from as is are was were be been our we its their this "
    "that these those it has have had will shall can may also which who all any".split()
)


def is_statement(text: str) -> bool:
    """A retrievable unit: at least `MIN_STATEMENT_WORDS` whitespace-separated words."""
    return len(text.split()) >= MIN_STATEMENT_WORDS


def tokens(text: str, *, drop_stopwords: bool = True, min_len: int = 3) -> list[str]:
    """Lowercased alphanumeric tokens, the lexical unit BM25 and overlap scoring share."""
    out = _TOKEN.findall(text.lower())
    if drop_stopwords:
        out = [t for t in out if t not in STOPWORDS]
    return [t for t in out if len(t) >= min_len]
