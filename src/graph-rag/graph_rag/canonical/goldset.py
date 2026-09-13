"""Gold clustering for canonicalisation: pooled annotation, then CESI metrics.

There is no knowledge base to link aspect phrases to (CESI and Galárraga et al. use Freebase-linked
entities), so gold clusters are built by annotation. A random sample of phrases would be almost all
singletons and leave the pairwise metrics undefined, so annotators partition **pools** of candidate
phrases. [project] To avoid tuning the gold towards the method being evaluated, each pool mixes
three sources: embedding neighbours, lexical (token Jaccard) neighbours, and random phrases from the
same category. Pools are disjoint, split alternately into validation (threshold tuning, as in CESI)
and test (reported numbers).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

from graph_rag.canonical.cluster import Phrase
from graph_rag.canonical.evaluate import cesi_metrics


def _tokens(s: str) -> set[str]:
    return set(s.split())


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def form_id(p: Phrase) -> str:
    return f"{p.category}|{p.key}"


def build_pools(
    phrases: list[Phrase],
    vectors: np.ndarray,
    examples: dict[str, str],
    n_pools: int = 60,
    pool_size: int = 12,
    n_embed: int = 5,
    n_lexical: int = 4,
    n_random: int = 2,
    seed: int = 20260913,
    exclude: set[str] | None = None,
    split: str | None = None,
    prefix: str = "pool",
) -> list[dict]:
    """`exclude`: form ids that may not appear (e.g. every form of an earlier pool set), so a new test
    set shares no phrase with the pools that tuned the method. `split`: force one split for all pools."""
    rng = random.Random(seed)
    by_cat: dict[str, list[int]] = {}
    for i, p in enumerate(phrases):
        by_cat.setdefault(p.category, []).append(i)

    # anchors: at least 3 per category, the rest proportional to category size
    cats = sorted(by_cat)
    quota = {c: 3 for c in cats}
    remaining = n_pools - 3 * len(cats)
    total = sum(len(v) for v in by_cat.values())
    for c in cats:
        quota[c] += round(remaining * len(by_cat[c]) / total)

    excluded = exclude or set()
    used: set[int] = {i for i, p in enumerate(phrases) if form_id(p) in excluded}
    pools = []
    for cat in cats:
        idx = by_cat[cat]
        candidates = [i for i in idx if phrases[i].weight >= 1]
        rng.shuffle(candidates)
        made = 0
        for anchor in candidates:
            if made >= quota[cat]:
                break
            if anchor in used:
                continue
            free = [i for i in idx if i not in used and i != anchor]
            if len(free) < pool_size - 1:
                break
            sims = vectors[free] @ vectors[anchor]
            by_embed = [free[j] for j in np.argsort(-sims)[:n_embed]]
            by_lex = sorted(free, key=lambda i: -_jaccard(phrases[i].key, phrases[anchor].key))[:n_lexical]
            members = list(dict.fromkeys([anchor, *by_embed, *by_lex]))
            rest = [i for i in free if i not in members]
            members += rng.sample(rest, min(n_random, len(rest)))
            members = members[:pool_size]
            rng.shuffle(members)
            used.update(members)
            pool_id = f"{prefix}{len(pools) + 1:03d}"
            pools.append({
                "pool_id": pool_id,
                "split": split or ("val" if len(pools) % 2 == 0 else "test"),
                "category": cat,
                "forms": [
                    {"form_id": form_id(phrases[i]), "text": phrases[i].display or phrases[i].key,
                     "example": examples.get(form_id(phrases[i]), "")}
                    for i in members
                ],
            })
            made += 1
    return pools


def write_pools(pools: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for p in pools:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


def load_gold(pools_path: Path, labels_path: Path) -> dict[str, dict]:
    """Validate the annotator's partitions against the exported pools."""
    pools = {json.loads(line)["pool_id"]: json.loads(line)
             for line in pools_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    gold: dict[str, dict] = {}
    for line in labels_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        pool = pools.get(rec["pool_id"])
        if pool is None:
            raise ValueError(f"unknown pool {rec['pool_id']}")
        expected = {f["form_id"] for f in pool["forms"]}
        seen = [fid for g in rec["groups"] for fid in g]
        if sorted(seen) != sorted(expected):
            raise ValueError(f"{rec['pool_id']}: groups must cover every form exactly once")
        gold[rec["pool_id"]] = {"split": pool["split"], "groups": [set(g) for g in rec["groups"]]}
    return gold


def evaluate_against_gold(assignment: dict[str, str], gold: dict[str, dict], split: str) -> dict:
    """assignment: form_id -> predicted cluster id. Pools are kept disjoint by prefixing ids."""
    pred: dict[str, set[str]] = {}
    gold_clusters: list[set[str]] = []
    for pool_id, g in gold.items():
        if g["split"] != split:
            continue
        for grp in g["groups"]:
            gold_clusters.append({f"{pool_id}::{fid}" for fid in grp})
            for fid in grp:
                cid = assignment.get(fid, f"__singleton__{fid}")
                pred.setdefault(f"{pool_id}::{cid}", set()).add(f"{pool_id}::{fid}")
    return cesi_metrics(pred.values(), gold_clusters)
