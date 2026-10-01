"""Export annotation pools, then tune and report canonicalisation against the gold clustering.

Protocol (CESI, WWW 2018): the HAC threshold is chosen on held-out validation data; reported numbers
come from data the threshold never saw.

Selection criterion and gate — revised 2026-09-13 after the first run [project]:
the first version selected on the mean of macro, micro and pairwise F1 and gated on micro precision.
On our gold that is ill-posed: 87 % of gold clusters are singletons, so a method that merges nothing
scores micro precision 1.0 and macro/micro F1 0.95/0.94 on the test pools — better than any
clustering. Only the pairwise metrics separate methods here. Because a wrong merge fuses two unrelated
claims into one timeline, selection now maximises **pairwise F0.5** on validation (precision weighted
over recall) and the gate is **pairwise precision** on test. This change was made after the first
test numbers had been seen; it is disclosed in docs/graph-rag-notes/README.md, and a clean final
number needs fresh test pools.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from graph_rag.build.canonical import load_phrases
from graph_rag.canonical.cluster import hac_clusters
from graph_rag.canonical.embed import PhraseEmbedder
from graph_rag.canonical.goldset import build_pools, evaluate_against_gold, form_id, load_gold, write_pools
from graph_rag.config import GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore

THRESHOLDS = [round(x, 2) for x in np.arange(0.70, 0.99, 0.02)]
GATE = {"pairwise_precision": 0.80}


def _mean_f1(m: dict) -> float:
    return (m["macro"]["f1"] + m["micro"]["f1"] + m["pairwise"]["f1"]) / 3


def _pairwise_f05(m: dict) -> float:
    p, r = m["pairwise"]["precision"], m["pairwise"]["recall"]
    return 1.25 * p * r / (0.25 * p + r) if p + r else 0.0


def export_pools(
    cfg: GraphConfig,
    out_path: Path,
    n_pools: int = 60,
    exclude_pools: list[Path] | None = None,
    split: str | None = None,
    prefix: str = "pool",
    seed: int | None = None,
) -> dict:
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        phrases, _, examples = load_phrases(store)
    exclude = set()
    for path in exclude_pools or []:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                exclude.update(f["form_id"] for f in json.loads(line)["forms"])
    # Pools come from the local model on purpose: the gold must not be shaped by the embedder under test.
    vectors = PhraseEmbedder(backend="fastembed").embed([p.key for p in phrases])
    pools = build_pools(phrases, vectors, examples, n_pools=n_pools, seed=seed or cfg.seed,
                        exclude=exclude, split=split, prefix=prefix)
    write_pools(pools, out_path)
    return {
        "pools": len(pools),
        "forms": sum(len(p["forms"]) for p in pools),
        "val": sum(p["split"] == "val" for p in pools),
        "test": sum(p["split"] == "test" for p in pools),
        "excluded_forms": len(exclude),
        "path": str(out_path),
    }


def tune(cfg: GraphConfig, pools_path: Path, labels_path: Path) -> dict:
    gold = load_gold(pools_path, labels_path)
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        phrases, _, _ = load_phrases(store)
    embedder = PhraseEmbedder()
    vectors = embedder.embed([p.key for p in phrases])
    ids = [form_id(p) for p in phrases]

    def assign_exact() -> dict[str, str]:
        # every morph phrase is its own cluster: this is the Morph Norm baseline on pool forms
        return {fid: fid for fid in ids}

    def assign_hac(t: float) -> dict[str, str]:
        out = {}
        for n, members in enumerate(hac_clusters(phrases, vectors, t)):
            for i in members:
                out[ids[i]] = f"c{n}"
        return out

    report: dict = {"morph": {s: evaluate_against_gold(assign_exact(), gold, s) for s in ("val", "test")}}
    sweep = []
    for t in THRESHOLDS:
        m = evaluate_against_gold(assign_hac(t), gold, "val")
        sweep.append({"threshold": t, "pairwise_f05": _pairwise_f05(m), "mean_f1": _mean_f1(m), "metrics": m})
    best = max(sweep, key=lambda r: (r["pairwise_f05"], r["threshold"]))
    test = evaluate_against_gold(assign_hac(best["threshold"]), gold, "test")
    report["hac"] = {"val_sweep": sweep, "best_threshold": best["threshold"], "test": test}

    summary = {
        "embedder": embedder.label,
        "pools": {"val": sum(g["split"] == "val" for g in gold.values()),
                  "test": sum(g["split"] == "test" for g in gold.values())},
        "morph_test_mean_f1": round(_mean_f1(report["morph"]["test"]), 4),
        "hac_best_threshold": best["threshold"],
        "selection": "max pairwise F0.5 on val",
        "hac_val_pairwise_f05": round(best["pairwise_f05"], 4),
        "hac_test": {k: {kk: round(vv, 4) for kk, vv in test[k].items() if isinstance(vv, float)}
                     for k in ("macro", "micro", "pairwise")},
        "hac_test_mean_f1": round(_mean_f1(test), 4),
        "morph_test_pairwise": {k: round(v, 4) for k, v in report["morph"]["test"]["pairwise"].items()
                                if isinstance(v, float)},
        "gate": {"pairwise_precision": test["pairwise"]["precision"] >= GATE["pairwise_precision"],
                 "threshold": GATE},
    }
    report["summary"] = summary
    out = cfg.out_dir / "canon_tuning.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def verify_eval(
    cfg: GraphConfig,
    pools_path: Path,
    labels_path: Path,
    split: str,
    variant: str = "rules",
    k: int = 5,
    floor: float = 0.70,
    workers: int = 8,
) -> dict:
    """Embeddings propose within each pool, the LLM verifies, clusters never cross a rejection."""
    from itertools import combinations

    from gw_common.llm import LLMClient

    from graph_rag.canonical.verify import candidate_pairs, cluster_from_verdicts, verify

    gold = load_gold(pools_path, labels_path)
    pools = {json.loads(line)["pool_id"]: json.loads(line)
             for line in pools_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        phrases, _, _ = load_phrases(store)
    embedder = PhraseEmbedder()
    vectors = embedder.embed([p.key for p in phrases])
    index = {form_id(p): i for i, p in enumerate(phrases)}

    texts = [p.display or p.key for p in phrases]
    examples = [""] * len(phrases)
    categories = [p.category for p in phrases]
    groups = []
    for pid, g in gold.items():
        if g["split"] != split:
            continue
        idx = []
        for f in pools[pid]["forms"]:
            i = index[f["form_id"]]
            texts[i], examples[i] = f["text"], f.get("example", "")
            idx.append(i)
        groups.append(idx)

    candidates = candidate_pairs(vectors, groups, k=k, floor=floor)
    client = LLMClient()
    verdicts = verify(client, candidates, texts, examples, categories, variant=variant, workers=workers)
    clusters = cluster_from_verdicts(len(phrases), verdicts)
    assignment = {form_id(phrases[i]): f"c{n}" for n, members in enumerate(clusters) for i in members}
    metrics = evaluate_against_gold(assignment, gold, split)

    # verifier accuracy on the candidate pairs it actually judged
    same_pairs = {frozenset(pr) for g in gold.values() if g["split"] == split
                  for grp in g["groups"] for pr in combinations(sorted(grp), 2)}
    tp = fp = fn = tn = 0
    for v in verdicts:
        truth = frozenset((form_id(phrases[v.a]), form_id(phrases[v.b]))) in same_pairs
        tp += v.same and truth
        fp += v.same and not truth
        fn += (not v.same) and truth
        tn += (not v.same) and (not truth)
    reachable = tp + fn
    result = {
        "split": split,
        "variant": variant,
        "k": k,
        "floor": floor,
        "embedder": embedder.label,
        "chat": client.settings.describe(),
        "candidates": len(candidates),
        "gold_pairs": sum(1 for _ in same_pairs),
        "gold_pairs_among_candidates": reachable,
        "verifier_confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "temperature_applied": None,
        "usage": client.usage,
        "metrics": metrics,
        "pairwise_f05": _pairwise_f05(metrics),
    }
    out = cfg.out_dir / f"canon_verify_{split}_{variant.replace('+', '_')}_k{k}_f{int(floor * 100)}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
