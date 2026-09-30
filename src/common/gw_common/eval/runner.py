"""Task orchestration: load a frozen dataset, run a system per evidence condition, write a run dir.

The harness owns the loop, the metrics and the manifest. A system only answers `classify` and
`retrieve`, so every arm is measured the same way.

Three things the design insists on:

- **Repeats, not single runs.** The classifier is a sampling LLM whose labels move ~10 % between
  identical runs, so a condition is run `repeats` times and reported as mean +- sd, with the
  baseline's own rep-to-rep churn as the noise floor a delta has to clear.
- **Retrieval once per condition.** Retrieval is deterministic, so evidence is collected once and
  reused across repeats; only the classifier is re-sampled.
- **Everything is recorded.** Per-rep predictions, evidence, model settings, split and slice all land
  in the run directory, so a number in the report can be traced back to its inputs.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from gw_common import datasets
from gw_common.eval import metrics as M
from gw_common.eval.exchange import align, read_evidence, read_predictions
from gw_common.eval.report import write_report
from gw_common.eval.select import SLICERS, describe, select
from gw_common.evidence import drop_target
from gw_common.registry import load as load_system
from gw_common.schemas import (
    EvidenceCondition,
    EvidenceSpan,
    GoldItem,
    Label,
    Prediction,
    Query,
    RunManifest,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNS_DIR = REPO_ROOT / "artifacts" / "runs"
EVIDENCE_K = 3
SLICE_REPORT_KEYS = ("row_type", "aspect_source", "category", "agreement", "gold")


def _git() -> tuple[str, bool]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True)
        return sha, bool(status.strip())
    except Exception:  # noqa: BLE001 - provenance is best effort, never fatal
        return "unknown", True


def build_query(item: GoldItem, condition: EvidenceCondition) -> Query:
    cross_year = condition.value.startswith("cross_year")
    return Query(
        text=item.text,
        company=item.company,
        aspect=item.aspect,
        year_from=None if cross_year else item.year,
        year_to=None if cross_year else item.year,
        anchor_year=item.year,
        target_text=item.text,
        condition=condition,
    )


def collect_evidence(
    system, items: list[GoldItem], condition: EvidenceCondition, k: int = EVIDENCE_K
) -> tuple[dict[str, list[EvidenceSpan]], int]:
    """Evidence per item, and how many returned spans were the target sentence itself.

    The harness removes the target whatever the retriever did, so no arm can score by re-reading the
    sentence it classifies; the count is reported so a retriever that leaks is visible.
    """
    retriever = getattr(system, "retriever", lambda: None)()
    if retriever is None or condition in (EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.LOCAL):
        return {}, 0
    evidence, dropped = {}, 0
    for it in items:
        q = build_query(it, condition)
        spans, n = drop_target(retriever.retrieve(q, k=k), q)
        evidence[it.item_id] = spans
        dropped += n
    return evidence, dropped


def evidence_stats(items: list[GoldItem], evidence: dict[str, list], target_dropped: int) -> dict:
    counts = [len(evidence.get(it.item_id, [])) for it in items]
    why = [s.why for spans in evidence.values() for s in spans]
    return {
        "items_with_evidence": sum(c > 0 for c in counts),
        "coverage": sum(c > 0 for c in counts) / len(counts) if counts else 0.0,
        "mean_spans": sum(counts) / len(counts) if counts else 0.0,
        "by_source": dict(sorted(Counter(why).items())),
        "target_dropped": target_dropped,
    }


def _rep_metrics(gold: list[Label], preds: list[Prediction]) -> dict:
    labels = [p.label for p in preds]
    return {
        "action": M.action_metrics(gold, labels),
        "pairdet": M.pairdet_metrics(gold, labels),
        "all_labels": M.classification_report(gold, labels),
        "ops": {
            **M.latency_summary([p.latency_ms for p in preds]),
            "input_tokens": sum(p.input_tokens for p in preds),
            "output_tokens": sum(p.output_tokens for p in preds),
            "llm_calls": sum(p.llm_calls for p in preds),
            "graph_hops": sum(p.graph_hops for p in preds),
        },
    }


def _mean_sd(values: list[float]) -> dict:
    return {"mean": statistics.fmean(values) if values else 0.0,
            "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
            "values": [round(v, 4) for v in values]}


def majority_labels(runs: list[list[Label]]) -> list[Label]:
    """Per item, the label most repeats agreed on; ties go to the first repeat (self-consistency)."""
    out = []
    for i in range(len(runs[0])):
        votes = Counter(run[i] for run in runs)
        best = max(votes.values())
        out.append(next(run[i] for run in runs if votes[run[i]] == best))
    return out


def instability(runs: list[list[Label]]) -> dict:
    """How often the same input gets different labels across repeats: the noise a delta must clear."""
    if len(runs) < 2:
        return {"unstable_items": None, "unstable_share": None}
    unstable = sum(len({run[i] for run in runs}) > 1 for i in range(len(runs[0])))
    return {"unstable_items": unstable, "unstable_share": unstable / len(runs[0])}


def slice_metrics(items: list[GoldItem], gold: list[Label], labels: list[Label]) -> dict:
    """Macro-F1 and accuracy per bucket, for the slices an error analysis actually asks for."""
    out: dict[str, dict] = {}
    for key in SLICE_REPORT_KEYS:
        fn = SLICERS[key]
        buckets: dict[str, list[int]] = {}
        for i, it in enumerate(items):
            bucket = fn(it)
            if bucket is not None:
                buckets.setdefault(str(bucket), []).append(i)
        rows = {}
        for bucket, idx in sorted(buckets.items()):
            g = [gold[i] for i in idx]
            p = [labels[i] for i in idx]
            action = M.action_metrics(g, p)
            rows[bucket] = {
                "n": len(idx),
                "n_action_rows": action["n"],
                "macro_f1": action["macro_f1"],
                "micro_f1": action["micro_f1"],
                "accuracy": M.classification_report(g, p)["accuracy"],
            }
        out[key] = rows
    return out


def run_task(
    system_name: str,
    task: str = "rq1",
    label_source: str = "human_majority",
    dataset_id: str = "gw1000",
    conditions: list[EvidenceCondition] | None = None,
    limit: int | None = None,
    out_root: Path | None = None,
    split: str | None = "dev",
    slices: dict[str, set[str]] | None = None,
    sample: int | None = None,
    repeats: int = 1,
    baseline: EvidenceCondition = EvidenceCondition.SENTENCE_ONLY,
    evidence_k: int = EVIDENCE_K,
    seed: int = 20260929,
    evidence_file: Path | None = None,
    predictions_file: Path | None = None,
) -> Path:
    started = datetime.now(UTC)
    t0 = time.perf_counter()
    if repeats > 1 and os.environ.get("GW_LLM_CACHE", "1") != "0":
        # A cached call replays the first answer, so repeats would measure nothing. Sampling afresh
        # is the point: the spread across repeats is the noise a condition's delta has to clear.
        os.environ["GW_LLM_CACHE"] = "0"
        print(f"  repeats={repeats}: response cache bypassed so each repeat samples the model again")
    system = load_system(system_name)
    all_items, dataset_hash = datasets.load(dataset_id, label_source)
    items = select(all_items, split=split, slices=slices, sample=sample, limit=limit, seed=seed)
    if not items:
        raise ValueError("no items selected: check --split / --slice / --sample")
    gold = [it.gold_label for it in items]
    eval_items = [it.to_eval_item() for it in items]

    wanted = conditions or system.supported_conditions()
    supported = set(system.supported_conditions())
    run_id = f"{started:%Y%m%dT%H%M%SZ}-{system_name}-{task}"
    run_dir = (out_root or RUNS_DIR) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    baseline_runs: list[list[Label]] | None = None
    with (run_dir / "predictions.jsonl").open("w", encoding="utf-8") as fp, \
         (run_dir / "evidence.jsonl").open("w", encoding="utf-8") as ev_fp:
        for cond in wanted:
            clf = system.classifier() if cond in supported else None
            if clf is None and predictions_file is None:
                results[cond.value] = {"status": "n/a"}
                continue
            if evidence_file is not None:
                supplied = read_evidence(evidence_file)
                spans_per_item, missing = align(items, supplied, "evidence")
                evidence, target_dropped = {}, 0
                for it, spans in zip(items, spans_per_item, strict=True):
                    kept, n = drop_target(list(spans or [])[:evidence_k], build_query(it, cond))
                    evidence[it.item_id] = kept
                    target_dropped += n
                if missing:
                    print(f"  {len(missing)} items had no evidence in {evidence_file.name}")
            else:
                evidence, target_dropped = collect_evidence(system, items, cond, evidence_k)
            for item_id, spans in evidence.items():
                ev_fp.write(json.dumps({"condition": cond.value, "item_id": item_id,
                                        "spans": [s.model_dump(mode="json") for s in spans]}) + "\n")

            reps, runs = [], []
            for rep in range(repeats if predictions_file is None else 1):
                if predictions_file is not None:
                    supplied, _ = align(items, read_predictions(predictions_file), "predictions")
                    preds = [p or Prediction(item_id=it.item_id, label=Label.INDETERMINATE)
                             for it, p in zip(items, supplied, strict=True)]
                else:
                    preds = clf.classify(eval_items, condition=cond, evidence=evidence or None)
                for p in preds:
                    fp.write(json.dumps({"condition": cond.value, "rep": rep,
                                         **p.model_dump(mode="json")}) + "\n")
                reps.append(_rep_metrics(gold, preds))
                runs.append([p.label for p in preds])

            vote = majority_labels(runs)
            block = {
                "status": "ok",
                "repeats": len(reps),
                "reps": reps,
                "aggregate": {
                    "macro_f1": _mean_sd([r["action"]["macro_f1"] for r in reps]),
                    "micro_f1": _mean_sd([r["action"]["micro_f1"] for r in reps]),
                    "accuracy": _mean_sd([r["action"]["accuracy"] for r in reps]),
                    "pairdet_f1": _mean_sd([r["pairdet"]["f1"] for r in reps]),
                    **instability(runs),
                },
                "majority": {"action": M.action_metrics(gold, vote),
                             "pairdet": M.pairdet_metrics(gold, vote),
                             "all_labels": M.classification_report(gold, vote)},
                "bootstrap": M.bootstrap_ci(gold, vote),
                "slices": slice_metrics(items, gold, vote),
            }
            if evidence:
                block["evidence"] = evidence_stats(items, evidence, target_dropped)
            if cond is baseline:
                baseline_runs = runs
            elif baseline_runs is not None:
                base_vote = majority_labels(baseline_runs)
                pooled = Counter()
                for b, n in zip(baseline_runs, runs, strict=True):
                    f = M.flip_analysis(gold, b, n)
                    pooled.update({k: v for k, v in f.items() if isinstance(v, int)})
                block["vs_baseline"] = {
                    "baseline": baseline.value,
                    "delta_macro_f1_mean": block["aggregate"]["macro_f1"]["mean"]
                    - results[baseline.value]["aggregate"]["macro_f1"]["mean"],
                    "delta_macro_f1_majority": block["majority"]["action"]["macro_f1"]
                    - results[baseline.value]["majority"]["action"]["macro_f1"],
                    "flips_pooled": dict(pooled),
                    "mcnemar_majority": M.mcnemar(gold, base_vote, vote),
                    "noise_floor": results[baseline.value]["aggregate"].get("unstable_items"),
                }
            results[cond.value] = block

    sha, dirty = _git()
    try:
        from gw_common.llm import LLMSettings

        llm_info = LLMSettings.from_env().describe()
    except Exception:  # noqa: BLE001 - a system may not use an LLM at all
        llm_info = {}
    manifest = RunManifest(
        run_id=run_id,
        system=system_name,
        task=task,
        conditions=wanted,
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        label_source=label_source,
        n_items=len(items),
        git_sha=sha,
        git_dirty=dirty,
        llm=llm_info,
        repeats=repeats,
        seed=seed,
        started_at=started.isoformat(),
        finished_at=datetime.now(UTC).isoformat(),
        wall_seconds=time.perf_counter() - t0,
        config={"split": split, "slices": {k: sorted(v) for k, v in (slices or {}).items()},
                "sample": sample, "limit": limit, "evidence_k": evidence_k,
                "baseline": baseline.value, "selection": describe(items)},
    )
    (run_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "metrics.json").write_text(
        json.dumps({"run_id": run_id, "system": system_name, "task": task,
                    "label_source": label_source, "dataset_hash": dataset_hash,
                    "n_items": len(items), "repeats": repeats, "conditions": results}, indent=2),
        encoding="utf-8",
    )
    write_report(run_dir, manifest, results)
    return run_dir


def compare(run_a: Path, run_b: Path) -> str:
    ma = json.loads((run_a / "metrics.json").read_text(encoding="utf-8"))
    mb = json.loads((run_b / "metrics.json").read_text(encoding="utf-8"))
    lines = ["# Compare", "", f"A = {ma['run_id']} ({ma['system']})",
             f"B = {mb['run_id']} ({mb['system']})", ""]
    if ma["dataset_hash"] != mb["dataset_hash"]:
        lines.append("> **WARNING** different dataset snapshots, the numbers are not comparable.\n")
    lines += ["| condition | A macro-F1 | B macro-F1 | delta |", "|---|---|---|---|"]
    for cond in sorted(set(ma["conditions"]) | set(mb["conditions"])):
        fa = ma["conditions"].get(cond, {}).get("aggregate", {}).get("macro_f1", {}).get("mean")
        fb = mb["conditions"].get(cond, {}).get("aggregate", {}).get("macro_f1", {}).get("mean")
        delta = f"{fb - fa:+.4f}" if fa is not None and fb is not None else "n/a"
        sa = "n/a" if fa is None else f"{fa:.4f}"
        sb = "n/a" if fb is None else f"{fb:.4f}"
        lines.append(f"| {cond} | {sa} | {sb} | {delta} |")
    return "\n".join(lines)
