"""RQ2 as an evaluation task: a system's retriever under `promise_window`, the shared judge, the gold.

The loop mirrors the RQ1 runner's three insistences: the judge is a sampling model, so every promise is
judged `repeats` times and reported as mean ± sd with a majority vote; retrieval runs once per promise and
is timed; everything lands in the run directory (manifest, evidence, per-rep predictions, metrics,
report) in the shapes `publish`, the results index and `--compare` read.

What a system contributes is `retrieve(query, k)` under the `promise_window` condition; what the
harness holds fixed is the judge (`gw_common.judges.promise`, v2 by default), the cap `k`, the gold
(`data/eval/rq2promises.*.jsonl`) and the split. Labels are the four reported outcomes; a `revised`
proposal counts as `failed`.
"""

from __future__ import annotations

import json
import os
import random
import re
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from gw_common import datasets
from gw_common.eval import ops
from gw_common.eval.exchange import read_evidence
from gw_common.eval.report import agent_section
from gw_common.eval.runner import RUNS_DIR, _git, retrieval_map
from gw_common.judges import promise as J
from gw_common.registry import load as load_system
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query, RunManifest

DATASET = "rq2promises"
LABEL_SOURCE = "pair_gold"
CONDITION = EvidenceCondition.PROMISE_WINDOW
K_WINDOW = 20  # statements per promise asked of a retriever; the graph finder's budgets stay under it
WORKERS = 8
_IDX = re.compile(r"p(\d+)s(\d+)$")


# --------------------------------------------------------------------------- queries and evidence rows
def query_of(promise: dict) -> str:
    return f"{promise['metric']}. {promise['origin'].get('target_text') or promise['origin'].get('text', '')}"


def promise_query(promise: dict) -> Query:
    """A promise as a `promise_window` query: the window on the query, the record under `meta`."""
    o = promise["origin"]
    return Query(
        text=query_of(promise),
        company=promise["company"],
        aspect=promise["metric"],
        year_from=o["year"] + 1,
        year_to=promise["target_year"] + 1,
        anchor_year=o["year"],
        target_text=o.get("text") or o.get("target_text"),
        condition=CONDITION,
        meta={"promise": promise},
    )


def _position(stmt_id: str | None) -> int:
    m = _IDX.search(stmt_id or "")
    return int(m.group(2)) if m else -1


def evidence_of(spans: list[EvidenceSpan]) -> list[dict]:
    """Spans into the rows the judge reads: report order, E-tags, and `follows` where one statement
    comes right after the previous one on the same page."""
    rows = sorted(
        (
            {
                "stmt_id": s.statement_id,
                "year": s.year,
                "page": s.page,
                "file": s.file,
                "text": s.text,
                "via": s.why,
            }
            for s in spans
        ),
        key=lambda r: (r["year"], r["file"] or "", r["page"] or 0, _position(r["stmt_id"])),
    )
    out = [{"ref": f"E{n}", **r} for n, r in enumerate(rows, 1)]
    for before, after in zip(out, out[1:], strict=False):
        same_place = (before["year"], before["file"], before["page"]) == (
            after["year"],
            after["file"],
            after["page"],
        )
        if same_place and _position(after["stmt_id"]) == _position(before["stmt_id"]) + 1:
            after["follows"] = before["ref"]
    return out


# --------------------------------------------------------------------------- the gold
def load_gold(split: str | None = None) -> tuple[list[dict], str]:
    """The frozen RQ2 gold (every row carries the promise record under `promise`), and its hash."""
    path = datasets.snapshot_path(DATASET, LABEL_SOURCE)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if split and split != "all":
        rows = [r for r in rows if r["split"] == split]
    return rows, path.name.split(".")[-2]


# --------------------------------------------------------------------------- metrics on the four outcomes
def kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    po = sum(x == y for x, y in zip(a, b, strict=True)) / len(a)
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / len(a) ** 2
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def outcome_metrics(gold: list[str], pred: list[str], classes: tuple[str, ...] = J.REPORTED) -> dict:
    """Accuracy, κ, macro-F1 over `classes`, per-class P/R/F1, the confusion matrix, and the three
    RQ2 rates: a verdict where the gold is unclear, unclear where the gold has a verdict, and how many
    verdicts are right."""
    n = len(gold)
    per_class, f1s = {}, []
    for c in classes:
        tp = sum(g == c and p == c for g, p in zip(gold, pred, strict=True))
        fp = sum(g != c and p == c for g, p in zip(gold, pred, strict=True))
        fn = sum(g == c and p != c for g, p in zip(gold, pred, strict=True))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[c] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
        f1s.append(f1)
    unclear = [(g, p) for g, p in zip(gold, pred, strict=True) if g == "unclear"]
    settled = [(g, p) for g, p in zip(gold, pred, strict=True) if g != "unclear"]
    said = [(g, p) for g, p in zip(gold, pred, strict=True) if p != "unclear"]
    return {
        "n": n,
        "accuracy": sum(g == p for g, p in zip(gold, pred, strict=True)) / n if n else 0.0,
        "cohen_kappa": kappa(gold, pred),
        "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
        "per_class": per_class,
        "confusion": {
            g: {p: sum(a == g and b == p for a, b in zip(gold, pred, strict=True)) for p in classes}
            for g in classes
        },
        "gold_distribution": dict(Counter(gold)),
        "system_distribution": dict(Counter(pred)),
        "over_commitment": _rate(sum(p != "unclear" for _, p in unclear), len(unclear)),
        "under_commitment": _rate(sum(p == "unclear" for _, p in settled), len(settled)),
        "verdict_precision": _rate(sum(g == p for g, p in said), len(said)),
    }


def _rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "share": k / n if n else None}


def bootstrap(gold: list[str], pred: list[str], draws: int = 1000, seed: int = 0) -> dict:
    """95 % intervals on accuracy and macro-F1 of the majority vote, resampling promises."""
    rng = random.Random(seed)
    n = len(gold)
    if n == 0:
        return {}
    acc, f1 = [], []
    for _ in range(draws):
        idx = [rng.randrange(n) for _ in range(n)]
        m = outcome_metrics([gold[i] for i in idx], [pred[i] for i in idx])
        acc.append(m["accuracy"])
        f1.append(m["macro_f1"])

    def ci(xs: list[float]) -> dict:
        xs = sorted(xs)
        return {"lo": xs[int(0.025 * len(xs))], "hi": xs[min(len(xs) - 1, int(0.975 * len(xs)))]}

    return {"accuracy": ci(acc), "macro_f1": ci(f1), "draws": draws}


def _mean_sd(values: list[float]) -> dict:
    return {
        "mean": statistics.fmean(values) if values else 0.0,
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
        "values": [round(v, 4) for v in values],
    }


# --------------------------------------------------------------------------- the task
def run_rq2(
    system_name: str,
    split: str = "dev",
    repeats: int = 3,
    k: int = K_WINDOW,
    limit: int | None = None,
    sample: int | None = None,
    seed: int = 20261030,
    out_root: Path | None = None,
    judge: str = J.DEFAULT_JUDGE,
    workers: int = WORKERS,
    client=None,
    evidence_file: Path | None = None,
) -> Path:
    """Retrieve the window evidence of every gold promise of `split` with the system's retriever, judge
    it `repeats` times with the shared judge, score the votes against the gold, write the run dir. With
    `evidence_file` (an earlier run's `evidence.jsonl`) nothing is retrieved, so judges compare on one
    evidence."""
    started = datetime.now(UTC)
    t0 = time.perf_counter()
    if repeats > 1 and client is None and os.environ.get("GW_LLM_CACHE", "1") != "0":
        os.environ["GW_LLM_CACHE"] = "0"
        print(f"  repeats={repeats}: response cache bypassed so each repeat samples the model again")
    system = load_system(system_name)
    if CONDITION not in system.supported_conditions():
        raise ValueError(f"{system_name} does not support the {CONDITION.value} condition")
    retriever = system.retriever() if evidence_file is None else None
    if retriever is None and evidence_file is None:
        raise ValueError(f"{system_name} has no retriever")
    rows, dataset_hash = load_gold(split)
    rows = [r for r in rows if r["outcome"] in J.REPORTED]
    if sample and sample < len(rows):
        rows = sorted(random.Random(seed).sample(rows, sample), key=lambda r: r["promise_id"])
    if limit:
        rows = rows[:limit]
    if not rows:
        raise ValueError("no promises selected: check --split / --sample")
    gold = [r["outcome"] for r in rows]

    run_id = f"{started:%Y%m%dT%H%M%SZ}-{system_name}-rq2"
    run_dir = (out_root or RUNS_DIR) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if client is None:
        from gw_common.llm import LLMClient

        client = LLMClient()
    settings = getattr(client, "settings", None)
    prompt = J.sections(J.PROMPTS[judge])

    # retrieval, once per promise, timed
    retrieval_ms: dict[str, float] = {}
    evidence: dict[str, list[dict]] = {}

    supplied = read_evidence(evidence_file) if evidence_file is not None else None

    def fetch(r: dict) -> tuple[list[EvidenceSpan], float]:
        if supplied is not None:
            return list(supplied.get(r["promise_id"], []))[:k], 0.0
        t = time.perf_counter()
        spans = retriever.retrieve(promise_query(r["promise"]), k=k)
        return spans, (time.perf_counter() - t) * 1000

    ordered = sorted(rows, key=lambda r: (r["promise"]["company"], r["promise"]["origin"]["year"]))
    with (run_dir / "evidence.jsonl").open("w", encoding="utf-8") as ev_fp:
        for r, (spans, ms) in zip(ordered, retrieval_map(fetch, ordered), strict=True):
            retrieval_ms[r["promise_id"]] = ms
            evidence[r["promise_id"]] = evidence_of(spans)
            ev_fp.write(
                json.dumps(
                    {
                        "condition": CONDITION.value,
                        "item_id": r["promise_id"],
                        "spans": [s.model_dump(mode="json") for s in spans],
                    }
                )
                + "\n"
            )
    retriever_info = retriever.describe() if hasattr(retriever, "describe") else {}
    if evidence_file is not None:
        retriever_info = {"evidence_from": Path(evidence_file).parent.name}

    # the judge, `repeats` times over identical evidence
    reps, runs, usage = [], [], []
    with (run_dir / "predictions.jsonl").open("w", encoding="utf-8") as fp:
        for rep in range(repeats):
            before = dict(getattr(client, "usage", {}))
            t_rep = time.perf_counter()

            def one(r: dict) -> dict:
                return J.JUDGES[judge](r["promise"], evidence[r["promise_id"]], client, prompt)

            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(one, rows))
            wall_s = time.perf_counter() - t_rep
            after = dict(getattr(client, "usage", {}))
            labels = [J.reported(res["outcome"]) for res in results]
            for r, res, lab in zip(rows, results, labels, strict=True):
                fp.write(
                    json.dumps(
                        {
                            "condition": CONDITION.value,
                            "rep": rep,
                            "item_id": r["promise_id"],
                            "label": lab,
                            "raw": res["outcome"],
                            "parse_ok": res["parse_ok"],
                            "evidence_refs": res["evidence_refs"],
                            "rationale": res["rationale"],
                            # what a rule can be re-run on without another call
                            **{k_: res[k_] for k_ in ("labels", "annual", "better", "basis") if k_ in res},
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            runs.append(labels)
            spent = {
                key: after.get(key, 0) - before.get(key, 0)
                for key in ("calls", "input_tokens", "output_tokens")
            }
            cost = settings.cost_usd(spent["input_tokens"], spent["output_tokens"]) if settings else None
            usage.append({**spent, "cost_usd": cost, "wall_s": wall_s})
            reps.append(
                {
                    **outcome_metrics(gold, labels),
                    "parse_ok_rate": sum(res["parse_ok"] for res in results) / len(results),
                    "usage": usage[-1],
                }
            )

    # the vote: the judge's own rule (strict majority, else unclear), then reported
    votes = [J.reported(J.vote([run[i] for run in runs])) for i in range(len(rows))]
    majority = outcome_metrics(gold, votes)
    by_source = {}
    for src in sorted({r["label_source"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["label_source"] == src]
        by_source[src] = outcome_metrics([gold[i] for i in idx], [votes[i] for i in idx])
    unstable = sum(len({run[i] for run in runs}) > 1 for i in range(len(rows))) if repeats > 1 else None
    n = len(rows)
    total_cost = sum(u["cost_usd"] for u in usage) if all(u["cost_usd"] is not None for u in usage) else None
    block = {
        "status": "ok",
        "repeats": repeats,
        "reps": reps,
        "aggregate": {
            "accuracy": _mean_sd([m["accuracy"] for m in reps]),
            "macro_f1": _mean_sd([m["macro_f1"] for m in reps]),
            "cohen_kappa": _mean_sd([m["cohen_kappa"] or 0.0 for m in reps]),
            "unstable_items": unstable,
            "unstable_share": unstable / n if unstable is not None else None,
        },
        "majority": {"action": majority, "by_source": by_source},
        "bootstrap": bootstrap(gold, votes, seed=seed),
        "evidence": {
            "coverage": sum(bool(v) for v in evidence.values()) / n,
            "mean_spans": sum(len(v) for v in evidence.values()) / n,
            "report_years_per_promise": sum(len({e["year"] for e in v}) for v in evidence.values()) / n,
            "by_source": dict(Counter(e.get("via", "") for v in evidence.values() for e in v)),
        },
        "speed_cost": {
            "retrieval": ops.retrieval_speed(retrieval_ms),
            "judge_calls_per_item": sum(u["calls"] for u in usage) / (n * repeats),
            "input_tokens_per_item": sum(u["input_tokens"] for u in usage) / (n * repeats),
            "output_tokens_per_item": sum(u["output_tokens"] for u in usage) / (n * repeats),
            "cost_usd_total": total_cost,
            "cost_per_1k_items_usd": total_cost / (n * repeats) * 1000 if total_cost is not None else None,
            "judge_wall_s_per_rep": statistics.fmean(u["wall_s"] for u in usage),
        },
    }
    agent_stats = getattr(retriever, "stats", None)
    if agent_stats is not None and (stats := agent_stats(CONDITION.value)):
        # Retrieval runs once per promise and the judge `repeats` times, so per promise end to end is one
        # planning plus one judgement.
        block["agent"] = stats
        price = settings.cost_usd if settings else None
        planner = (
            price(stats["input_tokens_per_item"], stats["output_tokens_per_item"]) if price else None
        )
        block["speed_cost"]["planner_cost_per_1k_items_usd"] = planner * 1000 if planner is not None else None
    results_json = {
        "run_id": run_id,
        "system": system_name,
        "task": "rq2",
        "label_source": LABEL_SOURCE,
        "dataset_hash": dataset_hash,
        "n_items": n,
        "repeats": repeats,
        "conditions": {CONDITION.value: block},
    }
    sha, dirty = _git()
    manifest = RunManifest(
        run_id=run_id,
        system=system_name,
        task="rq2",
        conditions=[CONDITION],
        dataset_id=DATASET,
        dataset_hash=dataset_hash,
        label_source=LABEL_SOURCE,
        n_items=n,
        git_sha=sha,
        git_dirty=dirty,
        llm=settings.describe() if settings is not None and hasattr(settings, "describe") else {},
        repeats=repeats,
        seed=seed,
        started_at=started.isoformat(),
        finished_at=datetime.now(UTC).isoformat(),
        wall_seconds=time.perf_counter() - t0,
        config={
            "split": split,
            "k": k,
            "sample": sample,
            "limit": limit,
            "judge": J.describe(judge),
            "classifier": {"style": f"judge-{judge}"},
            "retriever": retriever_info,
            "selection": {"label_source": dict(Counter(r["label_source"] for r in rows))},
        },
    )
    (run_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "metrics.json").write_text(json.dumps(results_json, indent=2), encoding="utf-8")
    (run_dir / "report.md").write_text(report(manifest, block), encoding="utf-8")
    return run_dir


def report(manifest: RunManifest, block: dict) -> str:
    agg, maj, sc, ev = block["aggregate"], block["majority"]["action"], block["speed_cost"], block["evidence"]
    cfg = manifest.config
    lines = [
        f"# {manifest.run_id}",
        "",
        f"- system: `{manifest.system}` · task: `rq2` · condition: `{CONDITION.value}`, k = {cfg.get('k')}",
        f"- gold: `{DATASET}` @ `{manifest.dataset_hash}` · n = {manifest.n_items} · split: "
        f"`{cfg.get('split')}` "
        f"· repeats: {manifest.repeats}",
        f"- judge: `{cfg.get('judge', {}).get('judge')}` · prompt `{cfg.get('judge', {}).get('prompt')}` "
        f"@ `{cfg.get('judge', {}).get('prompt_sha')}` · model: "
        f"`{manifest.llm.get('chat_model') or manifest.llm.get('model', '?')}` · "
        f"effort: `{manifest.llm.get('reasoning_effort', manifest.llm.get('effort', '?'))}`",
        f"- retriever: `{json.dumps(cfg.get('retriever') or {})}`",
        f"- git: `{manifest.git_sha[:8]}`{' (dirty)' if manifest.git_dirty else ''} · wall: "
        f"{manifest.wall_seconds:.1f}s",
        "",
        "| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ "
        "| unstable |",
        "|---|---|---|---|---|---|---|",
        f"| {agg['accuracy']['mean']:.4f} ±{agg['accuracy']['sd']:.3f} | {agg['macro_f1']['mean']:.4f} "
        f"±{agg['macro_f1']['sd']:.3f} | {agg['cohen_kappa']['mean']:.3f} | {maj['accuracy']:.4f} | "
        f"{maj['macro_f1']:.4f} | {maj['cohen_kappa']:.3f} | {agg['unstable_items']} |",
        "",
        "Bootstrap 95 % CI of the vote: accuracy "
        f"{block['bootstrap']['accuracy']['lo']:.3f}–{block['bootstrap']['accuracy']['hi']:.3f}, macro-F1 "
        f"{block['bootstrap']['macro_f1']['lo']:.3f}–{block['bootstrap']['macro_f1']['hi']:.3f}.",
        "",
        "## What a reader of the system's output can rely on (majority vote)",
        "",
        "| | k / n | share |",
        "|---|---|---|",
    ]
    for key, label in (
        ("over_commitment", "verdict where the gold is unclear"),
        ("under_commitment", "unclear where the gold has a verdict"),
        ("verdict_precision", "verdicts that are right"),
    ):
        r = maj[key]
        share = "—" if r["share"] is None else f"{r['share']:.3f}"
        lines.append(f"| {label} | {r['k']} / {r['n']} | {share} |")
    lines += [
        "",
        "## Per class (majority vote)",
        "",
        "| outcome | precision | recall | F1 | gold n | system n |",
        "|---|---|---|---|---|---|",
    ]
    for c, v in maj["per_class"].items():
        lines.append(
            f"| {c} | {v['precision']:.3f} | {v['recall']:.3f} | {v['f1']:.3f} | {v['support']} | "
            f"{maj['system_distribution'].get(c, 0)} |"
        )
    lines += ["", "Confusion, gold rows → system columns: " + json.dumps(maj["confusion"]), ""]
    lines += ["## By label source", "", "| source | n | accuracy | κ |", "|---|---|---|---|"]
    for src, v in block["majority"]["by_source"].items():
        lines.append(f"| {src} | {v['n']} | {v['accuracy']:.3f} | {v['cohen_kappa']:.3f} |")
    retr = sc["retrieval"] or {}
    lines += [
        "",
        "## Evidence, speed and cost",
        "",
        f"- evidence: coverage {ev['coverage']:.2f}, {ev['mean_spans']:.1f} statements per promise from "
        f"{ev['report_years_per_promise']:.1f} report years; by source {json.dumps(ev['by_source'])}",
        f"- retrieval: p50 {retr.get('p50_ms', 0):.0f} ms, p95 {retr.get('p95_ms', 0):.0f} ms per promise",
        f"- judge: {sc['judge_calls_per_item']:.2f} calls, {sc['input_tokens_per_item']:.0f} / "
        f"{sc['output_tokens_per_item']:.0f} tokens in / out per promise per repeat; "
        f"{sc['judge_wall_s_per_rep']:.0f} s per repeat; "
        + (
            "cost unknown (no prices set)"
            if sc["cost_usd_total"] is None
            else f"USD {sc['cost_usd_total']:.2f} in all, {sc['cost_per_1k_items_usd']:.2f} per 1,000 "
            "judgements"
        ),
    ]
    if sc.get("planner_cost_per_1k_items_usd") is not None:
        lines.append(f"- planner, on top of the judge: USD {sc['planner_cost_per_1k_items_usd']:.2f} per "
                     "1,000 promises (retrieval runs once per promise)")
    lines += agent_section({CONDITION.value: block})
    lines += [
        "",
        "Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.",
    ]
    return "\n".join(lines) + "\n"
