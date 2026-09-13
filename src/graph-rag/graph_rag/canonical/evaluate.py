"""Canonicalisation metrics, exactly as defined in CESI (Vashishth et al., WWW 2018, section 7.2),
following Galárraga et al. (2014).

C = predicted clusters, E = gold clusters, both over the same elements. F1 is the harmonic mean.

- macro precision: share of predicted clusters that are pure (fully inside one gold cluster);
  macro recall is the same with C and E swapped.
- micro precision: purity — for each predicted cluster, the size of its largest overlap with a gold
  cluster, summed, over N; micro recall swaps C and E.
- pairwise precision: same-gold pairs inside predicted clusters over all pairs inside predicted
  clusters; pairwise recall divides the same hits by all pairs inside gold clusters.

`tests/test_canonical.py` reproduces the worked example of CESI Figure 2 (P_macro = R_macro = 2/3,
P_micro = R_micro = 6/7, P_pair = 4/6, R_pair = 4/7).
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations


def _f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if p + r else 0.0


def _restrict(clusters: Iterable[Iterable[str]], universe: set[str]) -> list[set[str]]:
    out = []
    for c in clusters:
        kept = set(c) & universe
        if kept:
            out.append(kept)
    return out


def _macro(a: list[set[str]], b: list[set[str]]) -> float:
    return sum(any(x <= y for y in b) for x in a) / len(a) if a else 0.0


def _micro(a: list[set[str]], b: list[set[str]], n: int) -> float:
    if not n or not b:
        return 0.0
    return sum(max(len(x & y) for y in b) for x in a) / n


def _pairs(clusters: list[set[str]]) -> set[frozenset[str]]:
    return {frozenset(p) for c in clusters for p in combinations(sorted(c), 2)}


def cesi_metrics(predicted: Iterable[Iterable[str]], gold: Iterable[Iterable[str]]) -> dict:
    """Metrics over the elements that appear in both clusterings."""
    pred_sets = [set(p) for p in predicted]
    gold_sets = [set(g) for g in gold]
    universe = set().union(*gold_sets) if gold_sets else set()
    universe &= set().union(*pred_sets) if pred_sets else set()
    c = _restrict(pred_sets, universe)
    e = _restrict(gold_sets, universe)
    n = len(universe)

    p_macro, r_macro = _macro(c, e), _macro(e, c)
    p_micro, r_micro = _micro(c, e, n), _micro(e, c, n)
    pc, pe = _pairs(c), _pairs(e)
    hits = len(pc & pe)
    p_pair = hits / len(pc) if pc else 1.0
    r_pair = hits / len(pe) if pe else 1.0
    return {
        "n_elements": n,
        "n_pred_clusters": len(c),
        "n_gold_clusters": len(e),
        "macro": {"precision": p_macro, "recall": r_macro, "f1": _f1(p_macro, r_macro)},
        "micro": {"precision": p_micro, "recall": r_micro, "f1": _f1(p_micro, r_micro)},
        "pairwise": {"precision": p_pair, "recall": r_pair, "f1": _f1(p_pair, r_pair),
                     "hits": hits, "pred_pairs": len(pc), "gold_pairs": len(pe)},
    }
