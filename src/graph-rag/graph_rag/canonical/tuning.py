"""Export annotation pools, then tune and report canonicalisation against the gold clustering.

Protocol (CESI, WWW 2018): the HAC threshold is chosen on held-out validation data; reported numbers
come from data the threshold never saw. Selection criterion [project]: the mean of macro, micro and
pairwise F1 on the validation pools, mirroring the row average CESI uses to compare methods.
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
# Gate for M2 (roadmap, mapped onto CESI metrics): micro precision is cluster purity.
GATE = {"micro_precision": 0.80}


def _mean_f1(m: dict) -> float:
    return (m["macro"]["f1"] + m["micro"]["f1"] + m["pairwise"]["f1"]) / 3


def export_pools(cfg: GraphConfig, out_path: Path, n_pools: int = 60) -> dict:
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        phrases, _, examples = load_phrases(store)
    # Pools come from the local model on purpose: the gold must not be shaped by the embedder under test.
    vectors = PhraseEmbedder(backend="fastembed").embed([p.key for p in phrases])
    pools = build_pools(phrases, vectors, examples, n_pools=n_pools, seed=cfg.seed)
    write_pools(pools, out_path)
    return {
        "pools": len(pools),
        "forms": sum(len(p["forms"]) for p in pools),
        "val": sum(p["split"] == "val" for p in pools),
        "test": sum(p["split"] == "test" for p in pools),
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
        sweep.append({"threshold": t, "mean_f1": _mean_f1(m), "metrics": m})
    best = max(sweep, key=lambda r: (r["mean_f1"], r["threshold"]))
    test = evaluate_against_gold(assign_hac(best["threshold"]), gold, "test")
    report["hac"] = {"val_sweep": sweep, "best_threshold": best["threshold"], "test": test}

    summary = {
        "embedder": embedder.label,
        "pools": {"val": sum(g["split"] == "val" for g in gold.values()),
                  "test": sum(g["split"] == "test" for g in gold.values())},
        "morph_test_mean_f1": round(_mean_f1(report["morph"]["test"]), 4),
        "hac_best_threshold": best["threshold"],
        "hac_val_mean_f1": round(best["mean_f1"], 4),
        "hac_test": {k: {kk: round(vv, 4) for kk, vv in test[k].items() if isinstance(vv, float)}
                     for k in ("macro", "micro", "pairwise")},
        "hac_test_mean_f1": round(_mean_f1(test), 4),
        "gate": {"micro_precision": test["micro"]["precision"] >= GATE["micro_precision"],
                 "threshold": GATE},
    }
    report["summary"] = summary
    out = cfg.out_dir / "canon_tuning.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
