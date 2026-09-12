"""All metrics live here. A system that computes its own score does not get it into the report."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from gw_common.schemas import ACTION_LABELS, ALL_LABELS, Label


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def classification_report(
    gold: Sequence[Label], pred: Sequence[Label], labels: Sequence[Label] = ALL_LABELS
) -> dict:
    """Accuracy, per-label P/R/F1, macro-F1 over `labels`, and the confusion matrix."""
    assert len(gold) == len(pred), "gold/pred length mismatch"
    per_label = {}
    for lab in labels:
        tp = sum(g == lab and p == lab for g, p in zip(gold, pred, strict=True))
        fp = sum(g != lab and p == lab for g, p in zip(gold, pred, strict=True))
        fn = sum(g == lab and p != lab for g, p in zip(gold, pred, strict=True))
        p, r, f = _prf(tp, fp, fn)
        per_label[lab.value] = {"precision": p, "recall": r, "f1": f, "support": tp + fn}
    macro_f1 = sum(v["f1"] for v in per_label.values()) / len(per_label) if per_label else 0.0
    acc = sum(g == p for g, p in zip(gold, pred, strict=True)) / len(gold) if gold else 0.0
    pairs = list(zip(gold, pred, strict=True))
    confusion = {
        g.value: {p.value: sum(a == g and b == p for a, b in pairs) for p in ALL_LABELS}
        for g in ALL_LABELS
    }
    return {"n": len(gold), "accuracy": acc, "macro_f1": macro_f1, "per_label": per_label,
            "confusion": confusion}


def action_metrics(gold: Sequence[Label], pred: Sequence[Label]) -> dict:
    """rq1 primary: macro-F1 over the three actions, on rows whose gold is one of them."""
    pairs = [(g, p) for g, p in zip(gold, pred, strict=True) if g in ACTION_LABELS]
    if not pairs:
        return {"n": 0, "accuracy": 0.0, "macro_f1": 0.0, "per_label": {}, "confusion": {}}
    g2, p2 = zip(*pairs, strict=True)
    return classification_report(g2, p2, ACTION_LABELS)


def pairdet_metrics(gold: Sequence[Label], pred: Sequence[Label]) -> dict:
    """Binary: does the row carry a valid aspect-action at all (i.e. gold != none)."""
    g_bin = [g != Label.NONE for g in gold]
    p_bin = [p != Label.NONE for p in pred]
    tp = sum(g and p for g, p in zip(g_bin, p_bin, strict=True))
    fp = sum((not g) and p for g, p in zip(g_bin, p_bin, strict=True))
    fn = sum(g and (not p) for g, p in zip(g_bin, p_bin, strict=True))
    tn = sum((not g) and (not p) for g, p in zip(g_bin, p_bin, strict=True))
    p, r, f = _prf(tp, fp, fn)
    acc = (tp + tn) / len(g_bin) if g_bin else 0.0
    return {"n": len(g_bin), "accuracy": acc, "precision": p, "recall": r, "f1": f,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def bootstrap_ci(
    gold: Sequence[Label],
    pred: Sequence[Label],
    metric: str = "macro_f1",
    n_boot: int = 1000,
    seed: int = 20260912,
    alpha: float = 0.05,
) -> dict:
    rng = np.random.default_rng(seed)
    idx = np.arange(len(gold))
    vals = []
    for _ in range(n_boot):
        take = rng.choice(idx, size=len(idx), replace=True)
        g = [gold[i] for i in take]
        p = [pred[i] for i in take]
        vals.append(action_metrics(g, p)[metric])
    lo, hi = np.quantile(vals, [alpha / 2, 1 - alpha / 2])
    return {"metric": metric, "mean": float(np.mean(vals)), "lo": float(lo), "hi": float(hi),
            "n_boot": n_boot}


def mcnemar(gold: Sequence[Label], pred_a: Sequence[Label], pred_b: Sequence[Label]) -> dict:
    """Exact binomial McNemar on the discordant pairs (a wrong/b right vs a right/b wrong)."""
    b = sum(ga == pa and gb != pb for ga, pa, gb, pb in zip(gold, pred_a, gold, pred_b, strict=True))
    c = sum(ga != pa and gb == pb for ga, pa, gb, pb in zip(gold, pred_a, gold, pred_b, strict=True))
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "p_value": 1.0}
    k = min(b, c)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2**n))
    return {"b": b, "c": c, "p_value": p}


def flip_analysis(gold: Sequence[Label], base: Sequence[Label], new: Sequence[Label]) -> dict:
    """How many predictions changed when evidence was added, and did the change help."""
    changed = [(g, b, n) for g, b, n in zip(gold, base, new, strict=True) if b != n]
    wrong_to_right = sum(b != g and n == g for g, b, n in changed)
    right_to_wrong = sum(b == g and n != g for g, b, n in changed)
    return {
        "changed": len(changed),
        "changed_share": len(changed) / len(gold) if gold else 0.0,
        "wrong_to_right": wrong_to_right,
        "right_to_wrong": right_to_wrong,
        "net": wrong_to_right - right_to_wrong,
    }


def latency_summary(latencies_ms: Sequence[float]) -> dict:
    if not latencies_ms:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0}
    a = np.asarray(latencies_ms, dtype=float)
    return {"p50_ms": float(np.percentile(a, 50)), "p95_ms": float(np.percentile(a, 95)),
            "mean_ms": float(a.mean())}


# ----------------------------------------------------------------- retrieval (used from M4 on)
def precision_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    top = ranked[:k]
    return sum(d in relevant for d in top) / k if k else 0.0


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    return sum(d in relevant for d in ranked[:k]) / len(relevant) if relevant else 0.0


def mrr(ranked: Sequence[str], relevant: set[str]) -> float:
    for i, d in enumerate(ranked, 1):
        if d in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevant: set[str], k: int = 10) -> float:
    dcg = sum((1.0 / math.log2(i + 1)) for i, d in enumerate(ranked[:k], 1) if d in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def wrong_company_at_k(hit_companies: Sequence[str], expected: str, k: int = 10) -> float:
    top = hit_companies[:k]
    return sum(c != expected for c in top) / len(top) if top else 0.0
