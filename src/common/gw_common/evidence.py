"""Evidence hygiene shared by the harness and every retriever.

Statement ids are system-specific (graph `stmt_id`, baseline chunk ids), so the harness cannot name the
target sentence by id. It is identified instead by where it lives and what it says: a span is the target
itself when it comes from the same report (company and year; the corpus keeps one report per
company-year) and its normalised text contains the target sentence. Chunk retrievers are covered by the
"contains" rule, sentence retrievers by equality.
"""

from __future__ import annotations

import re

from gw_common.schemas import EvidenceSpan, Query

_TOKEN = re.compile(r"[a-z0-9]+")
MIN_CONTAIN_TOKENS = 4  # below this, "contains" would match unrelated spans; require equality instead


def normalise(text: str) -> str:
    return " ".join(_TOKEN.findall(text.lower()))


def is_target_span(span: EvidenceSpan, query: Query) -> bool:
    if not query.target_text or query.anchor_year is None:
        return False
    if span.year != query.anchor_year or (query.company and span.company != query.company):
        return False
    target, text = normalise(query.target_text), normalise(span.text)
    if not target:
        return False
    if len(target.split()) < MIN_CONTAIN_TOKENS:
        return text == target
    return f" {target} " in f" {text} "


def drop_target(spans: list[EvidenceSpan], query: Query) -> tuple[list[EvidenceSpan], int]:
    kept = [s for s in spans if not is_target_span(s, query)]
    return kept, len(spans) - len(kept)
