"""The three decisions inside each label scheme, scored one at a time.

Both label sets answer, in order, the three questions the brief asks of a classification task whose data
contains neutral content: is there anything to decide (presence), can it be decided (decidability), and
which way does it go (direction).

    RQ1   none vs a valid aspect              ->  indeterminate vs a clear claim  ->  implemented vs planning
    RQ2   disappeared vs any later statement  ->  unclear vs a verdict            ->  achieved vs failed

`gw-eval --stages RUN [RUN ...]` scores every condition's majority vote of each run this way (a published
folder under `results/` is followed to its local run through the manifest's run id, since predictions stay
under `artifacts/runs/`). Each level scores the gold rows that reach it; a vote that left the cascade
earlier (`none` on a `planning` sentence, `unclear` on an `achieved` promise) counts as wrong there and as
a miss for the gold class, so a level's accuracy is the share of its gold rows the vote got right end to
end, and its macro-F1 is over the level's two classes.
"""

from __future__ import annotations

import json
from pathlib import Path

from gw_common import datasets
from gw_common.eval.compare import _votes
from gw_common.eval.runner import RUNS_DIR

Levels = tuple[tuple[str, dict[str, str]], ...]  # (level, gold label -> its class there), in order

RQ1_LEVELS: Levels = (
    ("presence", {"implemented": "valid", "planning": "valid", "indeterminate": "valid", "none": "none"}),
    ("decidability", {"implemented": "claim", "planning": "claim", "indeterminate": "indeterminate"}),
    ("direction", {"implemented": "implemented", "planning": "planning"}),
)
RQ2_LEVELS: Levels = (
    ("presence", {"achieved": "present", "failed": "present", "unclear": "present",
                  "disappeared": "disappeared"}),
    ("decidability", {"achieved": "verdict", "failed": "verdict", "unclear": "unclear"}),
    ("direction", {"achieved": "achieved", "failed": "failed"}),
)
LEVELS = {"rq1": RQ1_LEVELS, "rq2": RQ2_LEVELS}
LEFT = "left"  # a vote that left the cascade before this level


def cascade(gold: list[str], pred: list[str], levels: Levels) -> list[dict]:
    """Per level: the gold rows that reach it, accuracy, macro-F1 over its two classes, and how many
    votes had left the cascade before it."""
    out = []
    for name, to_class in levels:
        rows = [(to_class[g], to_class.get(p, LEFT))
                for g, p in zip(gold, pred, strict=True) if g in to_class]
        classes = list(dict.fromkeys(to_class.values()))
        f1s = []
        for c in classes:
            tp = sum(g == c and p == c for g, p in rows)
            fp = sum(g != c and p == c for g, p in rows)
            fn = sum(g == c and p != c for g, p in rows)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
        out.append({
            "level": name,
            "classes": classes,
            "n": len(rows),
            "accuracy": sum(g == p for g, p in rows) / len(rows) if rows else 0.0,
            "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
            "left": sum(p == LEFT for _, p in rows),
        })
    return out


def resolve(run: Path, runs_dir: Path = RUNS_DIR) -> Path:
    """A run directory, or a published copy whose predictions stay under `artifacts/runs/`."""
    if (run / "predictions.jsonl").exists():
        return run
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    local = runs_dir / manifest["run_id"]
    if not (local / "predictions.jsonl").exists():
        raise FileNotFoundError(f"{run}: no predictions here or under {local}")
    return local


def score_run(run: Path, runs_dir: Path = RUNS_DIR) -> dict:
    """Every condition's majority vote of one run, scored level by level against the gold."""
    run = resolve(run, runs_dir)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    task = "rq2" if manifest.get("task") == "rq2" else "rq1"
    if task == "rq2":
        from gw_common.eval import rq2 as R

        votes = _votes(run, str, tie="unclear")  # the judge's own rule, as the run's metrics use it
        gold = {r["promise_id"]: r["outcome"] for r in R.load_gold()[0]}
    else:
        votes = {c: {i: str(v) for i, v in by.items()} for c, by in _votes(run).items()}
        items, _ = datasets.load(manifest.get("dataset_id", "gw1000"),
                                 manifest.get("label_source", "human_majority"))
        gold = {it.item_id: str(it.gold_label) for it in items}
    conditions = {}
    for cond, by_item in votes.items():
        ids = [i for i in by_item if i in gold]
        conditions[cond] = cascade([gold[i] for i in ids], [by_item[i] for i in ids], LEVELS[task])
    return {"run_id": manifest["run_id"], "system": manifest.get("system"), "task": task,
            "conditions": conditions}


def report_md(scored: list[dict]) -> str:
    lines = ["# The three decisions, scored separately", "",
             "Majority votes; each level on the gold rows that reach it, a vote that left the cascade "
             "earlier counted wrong there and as a miss for the gold class.", "",
             "| run | condition | level | classes | n | accuracy | macro-F1 | left earlier |",
             "|---|---|---|---|---|---|---|---|"]
    for s in scored:
        for cond, levels in s["conditions"].items():
            for lv in levels:
                lines.append(f"| `{s['run_id']}` | {cond} | {lv['level']} | {' vs '.join(lv['classes'])} "
                             f"| {lv['n']} | {lv['accuracy']:.3f} | {lv['macro_f1']:.3f} | {lv['left']} |")
    return "\n".join(lines)
