"""Blind human spot-check of the canonicalisation gold.

Why: the canonicalisation gold was written by the same assistant that designed the pipeline and the
guideline, so
the gate result depends on how strict that gold is. A teammate labels a sample of phrase pairs
**without seeing the assistant's labels**; agreement (Cohen's kappa, plus raw agreement) then says how
far the gold can be trusted, and disagreements show whether the guideline is too strict or too loose.

Which pairs: in each sampled pool, every pair the gold merges plus every embedding-candidate pair
(top-k neighbours above the floor, the same proposals the verifier sees). Pairs that no method would
ever consider and that the gold keeps apart are trivial "different" and are left out, so reviewer
time goes to the decisions that matter.
"""

from __future__ import annotations

import csv
import json
import random
from itertools import combinations
from pathlib import Path

import numpy as np

LABELS = ("same", "different")


def export(
    pools_path: Path,
    labels_path: Path,
    vectors_by_form: dict[str, np.ndarray],
    out_dir: Path,
    n_pools: int = 10,
    k: int = 5,
    floor: float = 0.70,
    seed: int = 20260915,
) -> dict:
    pools = [json.loads(line) for line in pools_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    gold = {json.loads(line)["pool_id"]: [set(g) for g in json.loads(line)["groups"]]
            for line in labels_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    rng = random.Random(seed)
    sample = rng.sample(pools, min(n_pools, len(pools)))

    rows, key = [], []
    for pool in sample:
        forms = pool["forms"]
        ids = [f["form_id"] for f in forms]
        same = {frozenset(p) for g in gold[pool["pool_id"]] for p in combinations(sorted(g), 2)}
        vecs = np.vstack([vectors_by_form[i] for i in ids])
        sims = vecs @ vecs.T
        cand = set()
        for a in range(len(ids)):
            order = [b for b in np.argsort(-sims[a]) if b != a][:k]
            cand.update(frozenset((ids[a], ids[b])) for b in order if sims[a, b] >= floor)
        pairs = sorted(same | cand, key=lambda p: sorted(p))
        text = {f["form_id"]: f["text"] for f in forms}
        example = {f["form_id"]: f.get("example", "") for f in forms}
        for p in pairs:
            a, b = sorted(p)
            if rng.random() < 0.5:          # randomise order so position carries no signal
                a, b = b, a
            pair_id = f"{pool['pool_id']}:{len(rows) + 1:03d}"
            rows.append({"pair_id": pair_id, "category": pool["category"], "phrase_a": text[a],
                         "phrase_b": text[b], "example_a": example[a][:200], "example_b": example[b][:200],
                         "label": "", "unsure": "", "notes": ""})
            key.append({"pair_id": pair_id, "form_a": a, "form_b": b,
                        "gold": "same" if p in same else "different"})
    rng.shuffle(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    sheet = out_dir / "canon_spotcheck_pairs.csv"
    with sheet.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out_dir / "canon_spotcheck_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    return {"pools": [p["pool_id"] for p in sample], "pairs": len(rows),
            "gold_same": sum(k["gold"] == "same" for k in key), "sheet": str(sheet)}


def score(sheet_path: Path, key_path: Path) -> dict:
    key = {k["pair_id"]: k["gold"] for k in json.loads(key_path.read_text(encoding="utf-8"))}
    with sheet_path.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    pairs = [(key[r["pair_id"]], r["label"].strip().lower())
             for r in rows if r["label"].strip().lower() in LABELS]
    if not pairs:
        raise ValueError("no labelled rows (label must be 'same' or 'different')")
    n = len(pairs)
    agree = sum(g == h for g, h in pairs) / n
    p_g = sum(g == "same" for g, _ in pairs) / n
    p_h = sum(h == "same" for _, h in pairs) / n
    pe = p_g * p_h + (1 - p_g) * (1 - p_h)
    kappa = (agree - pe) / (1 - pe) if pe < 1 else 1.0
    confusion = {f"gold_{g}__human_{h}": sum(1 for x, y in pairs if x == g and y == h)
                 for g in LABELS for h in LABELS}
    return {"labelled_pairs": n, "raw_agreement": round(agree, 3), "cohen_kappa": round(kappa, 3),
            "confusion": confusion,
            "reading": "gold stricter than human" if confusion["gold_different__human_same"]
            > confusion["gold_same__human_different"] else "gold looser than or as strict as human"}
