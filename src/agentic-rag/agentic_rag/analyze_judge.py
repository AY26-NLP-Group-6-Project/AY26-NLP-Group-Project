"""What each of judge v3's features adds: the rule re-run on a run's saved labels, with no further model call.

The labels stay those of the v3 prompt, so this measures the rule's features, not the prompt's change from v2.
`uv run python -m agentic_rag.analyze_judge <rq2 run with judge v3> [--against <rq2 run>]`.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from gw_common.eval import metrics as M
from gw_common.eval import rq2 as R
from gw_common.judges import promise as J


def rerun(run_dir: Path, features: frozenset[str]) -> dict[str, str]:
    """promise -> the vote with the rule limited to `features`."""
    promises = {r["promise_id"]: r["promise"] for r in R.load_gold()[0]}
    per: dict[str, list[str]] = {}
    for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        p = json.loads(line)
        promise = promises[p["item_id"]]
        if not p["parse_ok"]:
            outcome = "unclear"
        elif p.get("labels"):
            outcome = J.decide_v3(p["labels"], p["annual"], promise, p.get("better"), features)[0]
        else:
            outcome = p["raw"]                       # nothing retrieved: no labels to re-read
        per.setdefault(p["item_id"], []).append(J.reported(outcome))
    return {i: J.reported(J.vote(v)) for i, v in per.items()}


def votes_of(run_dir: Path) -> dict[str, str]:
    per: dict[str, list[str]] = {}
    for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        p = json.loads(line)
        per.setdefault(p["item_id"], []).append(p["label"])
    return {i: J.reported(J.vote(v)) for i, v in per.items()}


def table(run_dir: Path, against: Path | None = None) -> str:
    gold = {r["promise_id"]: r["outcome"] for r in R.load_gold()[0]}
    rows = ["| features | accuracy | κ | macro-F1 | verdict where gold unclear | unclear where gold settled "
            "| verdicts right | flips against base | p |", "|---|---|---|---|---|---|---|---|---|"]
    base_votes = votes_of(against) if against else None
    names = sorted(J.V3_FEATURES)
    subsets = [c for n in range(len(names) + 1) for c in itertools.combinations(names, n)]
    for subset in subsets:
        v = rerun(run_dir, frozenset(subset))
        ids = sorted(v)
        g = [gold[i] for i in ids]
        pred = [v[i] for i in ids]
        m = R.outcome_metrics(g, pred)
        flips, p = "", ""
        if base_votes:
            b = [base_votes[i] for i in ids]
            f = M.flip_analysis(g, b, pred)
            flips = f"+{f['wrong_to_right']} / -{f['right_to_wrong']}"
            p = f"{M.mcnemar(g, b, pred)['p_value']:.3f}"
        over, under, right = m["over_commitment"], m["under_commitment"], m["verdict_precision"]
        rows.append(f"| {', '.join(subset) or '(none)'} | {m['accuracy']:.3f} | {m['cohen_kappa']:.2f} "
                    f"| {m['macro_f1']:.3f} | {over['k']} / {over['n']} | {under['k']} / {under['n']} "
                    f"| {right['k']} / {right['n']} | {flips} | {p} |")
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--against", type=Path)
    args = ap.parse_args()
    print(table(args.run_dir, args.against))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
