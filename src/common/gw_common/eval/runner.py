"""Task orchestration: load a frozen dataset, run a system per evidence condition, write a run dir.

The harness owns the loop, the metrics and the manifest. A system only answers `classify` (and,
from M4 on, `retrieve`), so every arm is measured the same way.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from gw_common import datasets
from gw_common.eval import metrics as M
from gw_common.eval.report import write_report
from gw_common.registry import load as load_system
from gw_common.schemas import (
    EvidenceCondition,
    GoldItem,
    Label,
    Prediction,
    Query,
    RunManifest,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNS_DIR = REPO_ROOT / "artifacts" / "runs"
EVIDENCE_K = 5


def _git() -> tuple[str, bool]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True)
        dirty = bool(status.strip())
        return sha, dirty
    except Exception:  # noqa: BLE001 - provenance is best effort, never fatal
        return "unknown", True


def _collect_evidence(system, items: list[GoldItem], condition: EvidenceCondition) -> dict[str, list]:
    retriever = system.retriever()
    if retriever is None or condition is EvidenceCondition.SENTENCE_ONLY:
        return {}
    evidence = {}
    for it in items:
        q = Query(
            text=it.text,
            company=it.company,
            aspect=it.aspect,
            year_from=None if condition.value.startswith("cross_year") else it.year,
            year_to=None if condition.value.startswith("cross_year") else it.year,
            exclude_statement_ids=[it.item_id],
            condition=condition,
        )
        evidence[it.item_id] = retriever.retrieve(q, k=EVIDENCE_K)
    return evidence


def _condition_metrics(gold: list[Label], preds: list[Prediction]) -> dict:
    pred_labels = [p.label for p in preds]
    return {
        "action": M.action_metrics(gold, pred_labels),
        "pairdet": M.pairdet_metrics(gold, pred_labels),
        "all_labels": M.classification_report(gold, pred_labels),
        "ops": {
            **M.latency_summary([p.latency_ms for p in preds]),
            "input_tokens": sum(p.input_tokens for p in preds),
            "output_tokens": sum(p.output_tokens for p in preds),
            "llm_calls": sum(p.llm_calls for p in preds),
            "graph_hops": sum(p.graph_hops for p in preds),
        },
    }


def run_task(
    system_name: str,
    task: str = "rq1",
    label_source: str = "llm_pre",
    dataset_id: str = "gw1000",
    conditions: list[EvidenceCondition] | None = None,
    limit: int | None = None,
    out_root: Path | None = None,
) -> Path:
    started = datetime.now(UTC)
    t0 = time.perf_counter()
    system = load_system(system_name)
    items, dataset_hash = datasets.load(dataset_id, label_source)
    if limit:
        items = items[:limit]
    gold = [it.gold_label for it in items]
    eval_items = [it.to_eval_item() for it in items]

    wanted = conditions or system.supported_conditions()
    supported = set(system.supported_conditions())
    run_id = f"{started:%Y%m%dT%H%M%SZ}-{system_name}-{task}"
    run_dir = (out_root or RUNS_DIR) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    baseline_labels: list[Label] | None = None
    with (run_dir / "predictions.jsonl").open("w", encoding="utf-8") as fp:
        for cond in wanted:
            if cond not in supported:
                results[cond.value] = {"status": "n/a"}
                continue
            evidence = _collect_evidence(system, items, cond)
            clf = system.classifier()
            if clf is None:
                results[cond.value] = {"status": "n/a"}
                continue
            preds = clf.classify(eval_items, condition=cond, evidence=evidence or None)
            for p in preds:
                fp.write(json.dumps({"condition": cond.value, **p.model_dump(mode="json")}) + "\n")
            block = {"status": "ok", **_condition_metrics(gold, preds)}
            labels = [p.label for p in preds]
            if cond is EvidenceCondition.SENTENCE_ONLY:
                baseline_labels = labels
            elif baseline_labels is not None:
                block["vs_sentence_only"] = {
                    "delta_macro_f1": block["action"]["macro_f1"]
                    - results["sentence_only"]["action"]["macro_f1"],
                    "flips": M.flip_analysis(gold, baseline_labels, labels),
                    "mcnemar": M.mcnemar(gold, baseline_labels, labels),
                }
            block["bootstrap"] = M.bootstrap_ci(gold, labels)
            results[cond.value] = block

    sha, dirty = _git()
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
        started_at=started.isoformat(),
        finished_at=datetime.now(UTC).isoformat(),
        wall_seconds=time.perf_counter() - t0,
    )
    (run_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "metrics.json").write_text(
        json.dumps({"run_id": run_id, "system": system_name, "task": task,
                    "label_source": label_source, "dataset_hash": dataset_hash,
                    "n_items": len(items), "conditions": results}, indent=2),
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
        a = ma["conditions"].get(cond, {})
        b = mb["conditions"].get(cond, {})
        fa = a.get("action", {}).get("macro_f1")
        fb = b.get("action", {}).get("macro_f1")
        delta = f"{fb - fa:+.4f}" if fa is not None and fb is not None else "n/a"
        sa = "n/a" if fa is None else f"{fa:.4f}"
        sb = "n/a" if fb is None else f"{fb:.4f}"
        lines.append(f"| {cond} | {sa} | {sb} | {delta} |")
    return "\n".join(lines)
