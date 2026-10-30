"""Comparing two runs the only way that survives the classifier's own noise: paired, on the same items.

`gw-eval --compare A B` lines up the two runs' majority-vote labels item by item and reports, for every
condition they share and for each run's best condition, the paired flips and McNemar p-value. A bare
difference of means is printed too, but it is the p-value that may be quoted (README §5).

Both runs must be on the same dataset snapshot and the same item selection; anything else is refused
rather than silently compared.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from gw_common import datasets
from gw_common.eval import metrics as M
from gw_common.schemas import Label


def _votes(run_dir: Path, labels=Label, tie: str | None = None) -> dict[str, dict[str, str]]:
    """Per condition and item, the label most repeats agreed on. `labels` converts the stored string
    (the RQ1 `Label` enum; RQ2 outcomes stay plain strings). With `tie`, a vote without a strict
    majority becomes that label, as the RQ2 judge's own rule has it (no reproduced verdict is no verdict)."""
    per: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        if line:
            p = json.loads(line)
            per[p["condition"]][p["item_id"]].append(labels(p["label"]))

    def majority(v: list) -> str:
        top, count = Counter(v).most_common(1)[0]
        return top if tie is None or count * 2 > len(v) else tie

    return {cond: {i: majority(v) for i, v in items.items()} for cond, items in per.items()}


def _best(metrics: dict) -> str | None:
    ok = {c: b for c, b in metrics["conditions"].items() if b.get("status") == "ok"}
    return max(ok, key=lambda c: ok[c]["majority"]["action"]["macro_f1"]) if ok else None


def compare(run_a: Path, run_b: Path) -> str:
    ma = json.loads((run_a / "metrics.json").read_text(encoding="utf-8"))
    mb = json.loads((run_b / "metrics.json").read_text(encoding="utf-8"))
    man_a = json.loads((run_a / "manifest.json").read_text(encoding="utf-8"))
    man_b = json.loads((run_b / "manifest.json").read_text(encoding="utf-8"))
    lines = ["# Compare", "", f"A = `{ma['run_id']}` ({ma['system']}, repeats {ma.get('repeats', 1)})",
             f"B = `{mb['run_id']}` ({mb['system']}, repeats {mb.get('repeats', 1)})", ""]
    if datasets.canonical_hash(ma["dataset_hash"]) != datasets.canonical_hash(mb["dataset_hash"]):
        lines.append("> **Refused**: different dataset snapshots "
                     f"(`{ma['dataset_hash']}` vs `{mb['dataset_hash']}`); the items are not the same.")
        return "\n".join(lines)
    if ma["dataset_hash"] != mb["dataset_hash"]:
        lines.append(f"> Snapshots `{ma['dataset_hash']}` and `{mb['dataset_hash']}` are recorded as "
                     "equivalent (same items, labels and split; metadata differs).")
    for key in ("style",):
        ca = (man_a.get("config", {}).get("classifier") or {}).get(key)
        cb = (man_b.get("config", {}).get("classifier") or {}).get(key)
        if ca != cb:
            lines.append(f"> Note: classifier {key} differs (`{ca}` vs `{cb}`); "
                         "the comparison includes that change.")

    rq2 = man_a.get("task") == "rq2"
    if rq2 != (man_b.get("task") == "rq2"):
        lines.append("> **Refused**: one run is an RQ2 run and the other is not.")
        return "\n".join(lines)
    if rq2:
        from gw_common.eval import rq2 as R

        va, vb = _votes(run_a, str, tie="unclear"), _votes(run_b, str, tie="unclear")
        gold_by_id = {r["promise_id"]: r["outcome"] for r in R.load_gold()[0]}
        macro_f1 = lambda gold, pred: R.outcome_metrics(gold, pred)["macro_f1"]  # noqa: E731
    else:
        va, vb = _votes(run_a), _votes(run_b)
        items, _ = datasets.load(ma.get("dataset_id", man_a["dataset_id"]), ma["label_source"])
        gold_by_id = {it.item_id: it.gold_label for it in items}
        macro_f1 = lambda gold, pred: M.action_metrics(gold, pred)["macro_f1"]  # noqa: E731

    def paired(ca: str, cb: str) -> tuple[str, str, str, str, str] | None:
        shared = sorted(set(va[ca]) & set(vb[cb]), key=lambda i: int(i) if i.isdigit() else i)
        if not shared:
            return None
        gold = [gold_by_id[i] for i in shared]
        la, lb = [va[ca][i] for i in shared], [vb[cb][i] for i in shared]
        fa, fb = macro_f1(gold, la), macro_f1(gold, lb)
        flips = M.flip_analysis(gold, la, lb)
        p = M.mcnemar(gold, la, lb)["p_value"]
        return (f"{len(shared)}", f"{fa:.4f}", f"{fb:.4f}",
                f"+{flips['wrong_to_right']} / -{flips['right_to_wrong']}", f"{p:.3f}")

    lines += ["Majority-vote labels, paired on the items both runs scored.", "",
              "| A condition | B condition | items | A macro-F1 | B macro-F1 "
              "| flips A→B (right / wrong) | p (McNemar) |",
              "|---|---|---|---|---|---|---|"]
    rows = [(c, c) for c in sorted(set(va) & set(vb))]
    best_a, best_b = _best(ma), _best(mb)
    if best_a and best_b and (best_a, best_b) not in rows:
        rows.append((best_a, best_b))
    for ca, cb in rows:
        result = paired(ca, cb)
        if result is None:
            lines.append(f"| {ca} | {cb} | 0 | — | — | — | no shared items |")
            continue
        tag = " (best vs best)" if (ca, cb) == (best_a, best_b) and ca != cb else ""
        lines.append(f"| {ca}{tag} | {cb} | " + " | ".join(result) + " |")
    lines += ["", "Read the p-value, not the difference of means: identical configurations re-run differ by "
                  "a few points on their own."]
    return "\n".join(lines)


def publish(run_dir: Path, results_root: Path, note: str = "", name: str | None = None) -> Path:
    """Copy the small, shareable parts of a run into the versioned results folder.

    manifest, metrics, report and the RAG-metric summaries travel; predictions and evidence stay local
    (they are large and reproducible from the manifest). `name` is the folder the copy gets, as
    `<group>/<what-it-is>` (for example `baseline/statement-hybrid`): the run id stays in the manifest,
    the folder name says what the run was. A one-line note says what it was for.
    """
    out = results_root / (name or run_dir.name)
    out.mkdir(parents=True, exist_ok=True)
    for file in ("manifest.json", "metrics.json", "report.md", "ragas.json", "ragas.md",
                 "ragas_check_result.json"):
        src = run_dir / file
        if src.exists():
            out.joinpath(file).write_bytes(src.read_bytes())
    if note:
        out.joinpath("NOTE.md").write_text(note.strip() + "\n", encoding="utf-8")
    write_index(results_root)
    return out


def published_runs(results_root: Path) -> list[Path]:
    """Every published run under the results folder: `<group>/<name>/`, or `<name>/` from before groups."""
    runs = []
    for group in sorted(p for p in results_root.iterdir() if p.is_dir()):
        if (group / "manifest.json").exists():
            runs.append(group)
            continue
        runs += sorted(p for p in group.iterdir() if p.is_dir() and (p / "manifest.json").exists())
    return runs


def write_index(results_root: Path) -> Path:
    rows = []
    for d in published_runs(results_root):
        man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        met = json.loads((d / "metrics.json").read_text(encoding="utf-8"))
        best = _best(met)
        score = met["conditions"][best]["majority"]["action"]["macro_f1"] if best else None
        note = (d / "NOTE.md").read_text(encoding="utf-8").strip() if (d / "NOTE.md").exists() else ""
        rel = d.relative_to(results_root).as_posix()
        style = (man.get("config", {}).get("classifier") or {}).get("style", "label")
        rows.append(f"| [{rel}]({rel}/report.md) | {man['system']} | {style} | {_store(man)} "
                    f"| {man['config'].get('split')} "
                    f"| {man['n_items']} | {man.get('repeats', 1)} | {man['dataset_hash']} "
                    f"| {best or '—'} | {'—' if score is None else f'{score:.4f}'} | {note} "
                    f"| `{man['run_id']}` |")
    index = results_root / "README.md"
    index.write_text(
        "# Published runs\n\n"
        "Small, shareable copies of evaluation runs (manifest, metrics, report; the per-item predictions "
        "stay in `artifacts/runs/`). One folder per system family, one subfolder per run, named after "
        "what the run is. Add one with `gw-eval --publish artifacts/runs/<run_id> --name "
        "<group>/<name> --note \"...\"`; compare two with `gw-eval --compare <dir_a> <dir_b>`.\n\n"
        "The classifier column is the prompt style: `label` returns one word, `cited` a label with a "
        "rationale and citations; numbers across the two styles are not paired. The store column is "
        "what the retriever read (chunk store and its content hash, or the graph build). The run id is "
        "the local directory under `artifacts/runs/`.\n\n"
        "| run | system | classifier | store | split | items | repeats | snapshot | best condition "
        "| vote macro-F1 | note | run id |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    return index


def _store(manifest: dict) -> str:
    info = manifest.get("config", {}).get("retriever") or {}
    if info.get("store") == "graph":
        return f"graph `{info.get('graph_build_id')}`"
    if info.get("store"):
        return f"`{info['store']}` {info.get('chunks_sha256', '')}".strip()
    return "—"
