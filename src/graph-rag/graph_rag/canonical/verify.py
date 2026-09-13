"""Candidate merges proposed by embeddings, verified by an LLM (M2b).

Design, and where each part comes from:

- **Propose with embeddings, decide with an LLM.** EDC (Zhang & Soh, EMNLP 2024, section 3, phase 3)
  retrieves candidates by vector similarity and has an LLM verify each transformation "to prevent
  issues of over-generalization"; it reports that CESI's embedding clustering over-generalises
  (e.g. merging 'place of birth' and 'date of death'). Our first M2 run failed for the same reason.
- **Top-k candidates.** EDC retrieves the top-5 candidates per element; `k` and a similarity floor
  bound the number of LLM calls.
- **Forced binary answer and handwritten rules.** Peeters, Steiner & Bizer ("Entity Matching using
  Large Language Models", arXiv 2310.11244) evaluate forced Yes/No answers and natural-language
  matching rules; they also find no single best prompt and that demonstrations help only for some
  model/dataset pairs. So both variants ("rules", "rules+demos") are compared on validation pools
  only, and demonstrations are hand-written from the guideline, never taken from the pools.
- **No chaining through rejections** [project]: clusters are merged along accepted pairs in
  descending similarity, but two clusters never merge if any pair between them was rejected — the
  complete-linkage idea applied to verifier decisions, so A~B and B~C cannot silently force A~C.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from graph_rag.config import REPO_ROOT

PROMPT_PATH = REPO_ROOT / "configs" / "prompts" / "aspect_merge_verify.md"
VARIANTS = ("rules", "rules+demos")


@dataclass(slots=True)
class Candidate:
    a: int
    b: int
    similarity: float


@dataclass(slots=True)
class Verdict:
    a: int
    b: int
    similarity: float
    same: bool
    raw: str
    cached: bool
    input_tokens: int
    output_tokens: int


def _sections(path: Path = PROMPT_PATH) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## (system|demonstrations[^\n]*|user)\s*$", text, flags=re.M)
    out = {}
    for i in range(1, len(parts) - 1, 2):
        key = "demos" if parts[i].startswith("demonstrations") else parts[i]
        out[key] = parts[i + 1].strip()
    return out


def candidate_pairs(
    vectors: np.ndarray, groups: list[list[int]], k: int = 5, floor: float = 0.70
) -> list[Candidate]:
    """Within each group (a category block, or a pool), each item's top-k neighbours above `floor`."""
    seen: set[tuple[int, int]] = set()
    out: list[Candidate] = []
    for idx in groups:
        if len(idx) < 2:
            continue
        sims = vectors[idx] @ vectors[idx].T
        np.fill_diagonal(sims, -1.0)
        for row, i in enumerate(idx):
            order = np.argsort(-sims[row])[:k]
            for col in order:
                s = float(sims[row, col])
                if s < floor:
                    break
                j = idx[col]
                key = (min(i, j), max(i, j))
                if key not in seen:
                    seen.add(key)
                    out.append(Candidate(key[0], key[1], s))
    return out


def build_messages(category: str, a: tuple[str, str], b: tuple[str, str], variant: str) -> list[dict]:
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}")
    sec = _sections()
    system = sec["system"]
    if variant == "rules+demos":
        system += "\n\nExamples:\n" + sec["demos"]
    user = sec["user"].format(category=category, text_a=a[0], example_a=a[1][:200] or "-",
                              text_b=b[0], example_b=b[1][:200] or "-")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_yes_no(text: str) -> bool:
    """Strict parse: anything that is not clearly 'yes' counts as No (the prompt says: if unsure, No)."""
    return re.match(r"^\W*yes\b", text.strip(), flags=re.I) is not None


def verify(
    client,
    candidates: list[Candidate],
    texts: list[str],
    examples: list[str],
    categories: list[str],
    variant: str = "rules",
    workers: int = 8,
) -> list[Verdict]:
    def one(c: Candidate) -> Verdict:
        a, b = (texts[c.a], examples[c.a]), (texts[c.b], examples[c.b])
        msgs = build_messages(categories[c.a], a, b, variant)
        r = client.chat(msgs, max_tokens=512)
        return Verdict(c.a, c.b, c.similarity, parse_yes_no(r.text), r.text[:40], r.cached,
                       r.input_tokens, r.output_tokens)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, candidates))


def cluster_from_verdicts(n: int, verdicts: list[Verdict]) -> list[list[int]]:
    """Union accepted pairs in descending similarity, never across a rejected pair."""
    parent = list(range(n))
    members: dict[int, set[int]] = {i: {i} for i in range(n)}
    rejected: set[tuple[int, int]] = {(min(v.a, v.b), max(v.a, v.b)) for v in verdicts if not v.same}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for v in sorted((v for v in verdicts if v.same), key=lambda v: -v.similarity):
        ra, rb = find(v.a), find(v.b)
        if ra == rb:
            continue
        if any((min(x, y), max(x, y)) in rejected for x in members[ra] for y in members[rb]):
            continue
        parent[rb] = ra
        members[ra] |= members.pop(rb)
    return [sorted(m) for m in members.values()]
