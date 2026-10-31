"""Console entry points: gw-eval, gw-serve, gw-data.

Every command is a thin wrapper over functions in `gw_common.eval`, so the FastAPI layer can expose
the same operations without duplicating logic.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from gw_common import datasets, registry
from gw_common.eval import retrieval as retrieval_eval
from gw_common.eval.compare import compare, publish
from gw_common.eval.exchange import export_queries
from gw_common.eval.runner import EVIDENCE_K, REPO_ROOT, run_task
from gw_common.eval.select import SLICERS, describe, parse_slices, select
from gw_common.schemas import EvidenceCondition

RESULTS_DIR = REPO_ROOT / "results"


def eval_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("gw-eval", description="Run a registered system against a frozen dataset")
    ap.add_argument("--system")
    ap.add_argument("--task", default="rq1", choices=["rq1", "rq2", "pairdet", "retrieval", "trajectory"],
                    help="rq1: action classification under evidence conditions; rq2: promise outcomes "
                         "from the system's promise_window evidence, read by the shared judge")
    ap.add_argument("--labels", default="human_majority", help="label source, e.g. human_majority")
    ap.add_argument("--dataset", default="gw1000")
    ap.add_argument("--conditions", help="comma-separated; default = whatever the system supports")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"],
                    help="tune on dev; open test once for the report")
    ap.add_argument("--slice", dest="slices", help=f"e.g. row_type=aspect,category=workplace|management"
                                                   f" (keys: {', '.join(sorted(SLICERS))})")
    ap.add_argument("--sample", type=int, help="random subset of the selection, seeded")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--repeats", type=int, default=3,
                    help="repeat each condition; mean ± sd and a majority vote are reported")
    ap.add_argument("--baseline", default="sentence_only", help="condition that deltas are measured against")
    ap.add_argument("--k", type=int, help="evidence spans per item (default 3 for rq1, 20 for rq2)")
    ap.add_argument("--evidence", type=Path, help="score evidence produced outside this package")
    ap.add_argument("--predictions", type=Path, help="score labels produced outside this package")
    ap.add_argument("--export-queries", type=Path, metavar="OUT",
                    help="write the questions for one condition and exit")
    ap.add_argument("--queries", type=Path, help="retrieval task: query file (JSONL)")
    ap.add_argument("--qrels", type=Path, help="retrieval task: judgements (JSONL)")
    ap.add_argument("--export-pool", type=Path, metavar="OUT",
                    help="retrieval task: write a pooled judging sheet over --modes and exit")
    ap.add_argument("--modes", default="bm25,dense,rrf,rrf+rerank",
                    help="retrieval task: retriever configurations to compare")
    ap.add_argument("--ragas", type=Path, metavar="RUN_DIR",
                    help="score a finished run for faithfulness, answer relevance and context precision")
    ap.add_argument("--ragas-rep", type=int, default=0, help="which repeat's answers to score")
    ap.add_argument("--ragas-export-check", type=Path, metavar="CSV",
                    help="with --ragas: write a blind human spot-check sheet from the scored run")
    ap.add_argument("--ragas-score-check", type=Path, metavar="CSV",
                    help="with --ragas: judge-vs-human agreement on a returned sheet")
    ap.add_argument("--ragas-n", type=int, default=50, help="answers sampled into the spot-check sheet")
    ap.add_argument("--list", action="store_true", help="list registered systems and exit")
    ap.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"),
                    help="paired comparison of two runs' majority votes on the same items")
    ap.add_argument("--pairs", help="with --compare: extra condition pairs, condA:condB,condA:condB")
    ap.add_argument("--publish", type=Path, metavar="RUN_DIR",
                    help="copy manifest, metrics and reports of a run into results/ (versioned)")
    ap.add_argument("--note", default="", help="with --publish: one line on what the run was for")
    ap.add_argument("--name", help="with --publish: folder under results/, as <group>/<what-it-is>, "
                                   "e.g. baseline/statement-hybrid")
    args = ap.parse_args(argv)
    if args.k is None:
        args.k = 20 if args.task == "rq2" else EVIDENCE_K

    if args.list:
        for name, target in sorted(registry.available().items()):
            print(f"{name:22s} {target}")
        return 0
    if args.compare:
        pairs = [tuple(p.split(":", 1)) for p in (args.pairs or "").split(",") if p]
        print(compare(Path(args.compare[0]), Path(args.compare[1]), pairs))
        return 0
    if args.publish:
        out = publish(args.publish, RESULTS_DIR, args.note, args.name)
        print(f"published -> {out}")
        return 0
    if args.ragas:
        return _ragas(args)

    conditions = (
        [EvidenceCondition(c.strip()) for c in args.conditions.split(",")] if args.conditions else None
    )
    slices = parse_slices(args.slices)

    if args.export_queries:
        if not conditions or len(conditions) != 1:
            ap.error("--export-queries needs exactly one --conditions value")
        items, _ = datasets.load(args.dataset, args.labels)
        chosen = select(items, split=args.split, slices=slices, sample=args.sample, limit=args.limit)
        print(json.dumps(export_queries(chosen, conditions[0], args.export_queries, args.k), indent=2))
        return 0

    if not args.system:
        ap.error("--system is required (or use --list / --compare / --export-queries)")
    if args.task == "retrieval":
        return _retrieval(ap, args)
    if args.task == "rq2":
        from gw_common.eval import rq2

        run_dir = rq2.run_rq2(args.system, split=args.split, repeats=args.repeats, k=args.k,
                              limit=args.limit, sample=args.sample)
        print((run_dir / "report.md").read_text(encoding="utf-8"))
        print(f"run dir: {run_dir}")
        return 0
    run_dir = run_task(
        args.system,
        task=args.task,
        label_source=args.labels,
        dataset_id=args.dataset,
        conditions=conditions,
        limit=args.limit,
        split=args.split,
        slices=slices,
        sample=args.sample,
        repeats=args.repeats,
        baseline=EvidenceCondition(args.baseline),
        evidence_k=args.k,
        evidence_file=args.evidence,
        predictions_file=args.predictions,
    )
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    print(f"run: {run_dir}")
    for cond, block in metrics["conditions"].items():
        if block.get("status") != "ok":
            print(f"  {cond:22s} n/a")
            continue
        agg, vote = block["aggregate"], block["majority"]["action"]
        unstable = agg.get("unstable_items")
        print(
            f"  {cond:22s} macro-F1 {agg['macro_f1']['mean']:.4f} ± {agg['macro_f1']['sd']:.3f}"
            f"  micro-F1 {agg['micro_f1']['mean']:.4f}"
            f"  vote {vote['macro_f1']:.4f}"
            f"  unstable {'n/a' if unstable is None else unstable}/{metrics['n_items']}"
        )
    return 0


def _ragas(args) -> int:
    """Post-hoc answer-level metrics for a run directory, and the human spot-check around them."""
    from gw_common.eval import rag_metrics

    if args.ragas_score_check:
        print(json.dumps(rag_metrics.score_check(args.ragas, args.ragas_score_check), indent=2))
        return 0
    if args.ragas_export_check:
        print(json.dumps(rag_metrics.export_check(args.ragas, args.ragas_export_check, args.ragas_n),
                         indent=2))
        return 0
    conditions = [c.strip() for c in args.conditions.split(",")] if args.conditions else None
    summary = rag_metrics.score_run(args.ragas, conditions=conditions, rep=args.ragas_rep,
                                    sample=args.sample)
    print((args.ragas / "ragas.md").read_text(encoding="utf-8"))
    print(f"scored {summary['n_scored']} answers -> {args.ragas / 'ragas.json'}")
    return 0


def _retrieval(ap: argparse.ArgumentParser, args) -> int:
    """Rank-aware retrieval evaluation, run over one or more retriever configurations."""
    if not args.queries:
        ap.error("--queries is required for --task retrieval")
    queries = retrieval_eval.load_queries(args.queries)
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    results = {}
    for mode in modes:
        os.environ["GW_BASELINE_MODE"] = mode          # systems that support modes read this
        retriever = registry.load(args.system).retriever()
        if retriever is None:
            ap.error(f"system {args.system!r} has no retriever")
        results[mode] = retrieval_eval.run(retriever, queries, k=args.k)

    if args.export_pool:
        print(json.dumps(retrieval_eval.export_pool(results, queries, args.export_pool), indent=2))
        return 0
    if not args.qrels:
        ap.error("--qrels is required to score retrieval (or use --export-pool first)")
    qrels = retrieval_eval.load_qrels(args.qrels)
    summary = {mode: {k: v for k, v in retrieval_eval.score(per_query, qrels, queries, args.k).items()
                      if k != "per_query"}
               for mode, per_query in results.items()}
    print(json.dumps(summary, indent=2))
    return 0


def data_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("gw-data", description="Freeze and inspect evaluation snapshots")
    ap.add_argument("action", choices=["build", "list", "describe", "export-xls"])
    ap.add_argument("dataset", nargs="?", default="gw1000")
    ap.add_argument("--labels", default="human_majority")
    ap.add_argument(
        "--from", dest="source", type=Path, help="eval workbook (default: kb/annotation/eval.xlsx)"
    )
    ap.add_argument("--out", type=Path, help="export-xls: output path (default kb/annotation/eval.xls)")
    ap.add_argument("--slice", dest="slices")
    ap.add_argument("--split", default="all", choices=["dev", "test", "all"])
    args = ap.parse_args(argv)

    if args.action == "list":
        for p in sorted(datasets.EVAL_DIR.glob("*.jsonl")):
            print(p.name)
        return 0
    if args.action == "export-xls":
        from gw_common import annotation

        out = args.out or annotation.EVAL_XLSX.with_suffix(".xls")
        print(json.dumps(annotation.export_xls(out, args.source), indent=2))
        return 0
    if args.action == "describe":
        items, digest = datasets.load(args.dataset, args.labels)
        chosen = select(items, split=args.split, slices=parse_slices(args.slices))
        print(json.dumps({"dataset": args.dataset, "labels": args.labels, "hash": digest,
                          "selected": len(chosen), "of": len(items),
                          "counts": describe(chosen, keys=list(SLICERS))}, indent=2))
        return 0
    if args.dataset == "a3cg":
        for path, n, skipped in datasets.build_a3cg():
            print(f"wrote {path.name} ({n} items, {skipped} multi-action aspects skipped)")
        return 0
    if args.dataset != "gw1000":
        raise SystemExit(f"no builder for dataset {args.dataset!r} yet")
    from gw_common import annotation

    print(json.dumps(annotation.build(xlsx=args.source), indent=2))
    return 0


def serve_main(argv: list[str] | None = None) -> int:
    import uvicorn

    ap = argparse.ArgumentParser("gw-serve", description="Serve the systems over FastAPI")
    ap.add_argument("--systems", default="", help="comma-separated; default = all registered")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)

    from gw_common.api.app import create_app

    names = [s.strip() for s in args.systems.split(",") if s.strip()] or None
    uvicorn.run(create_app(names), host=args.host, port=args.port)
    return 0
