"""Console entry points: gw-eval, gw-serve, gw-data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gw_common import datasets, registry
from gw_common.eval.runner import compare, run_task
from gw_common.schemas import EvidenceCondition


def eval_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("gw-eval", description="Run a registered system against a frozen dataset")
    ap.add_argument("--system")
    ap.add_argument("--task", default="rq1", choices=["rq1", "pairdet", "retrieval", "trajectory"])
    ap.add_argument("--labels", default="llm_pre", choices=list(datasets.LABEL_SOURCES))
    ap.add_argument("--dataset", default="gw1000")
    ap.add_argument("--conditions", help="comma-separated; default = whatever the system supports")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--list", action="store_true", help="list registered systems and exit")
    ap.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"))
    args = ap.parse_args(argv)

    if args.list:
        for name, target in sorted(registry.available().items()):
            print(f"{name:22s} {target}")
        return 0
    if args.compare:
        print(compare(Path(args.compare[0]), Path(args.compare[1])))
        return 0
    if not args.system:
        ap.error("--system is required (or use --list / --compare)")

    conditions = (
        [EvidenceCondition(c.strip()) for c in args.conditions.split(",")] if args.conditions else None
    )
    run_dir = run_task(
        args.system,
        task=args.task,
        label_source=args.labels,
        dataset_id=args.dataset,
        conditions=conditions,
        limit=args.limit,
    )
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    print(f"run: {run_dir}")
    for cond, block in metrics["conditions"].items():
        if block.get("status") != "ok":
            print(f"  {cond:22s} n/a")
            continue
        print(
            f"  {cond:22s} macro-F1 {block['action']['macro_f1']:.4f}"
            f"  acc {block['action']['accuracy']:.4f}"
            f"  pairdet-F1 {block['pairdet']['f1']:.4f}"
            f"  p95 {block['ops']['p95_ms']:.1f} ms"
        )
    return 0


def data_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("gw-data", description="Freeze evaluation snapshots")
    ap.add_argument("action", choices=["build", "list"])
    ap.add_argument("dataset", nargs="?", default="gw1000")
    ap.add_argument("--labels", default="llm_pre", choices=list(datasets.LABEL_SOURCES))
    args = ap.parse_args(argv)

    if args.action == "list":
        for p in sorted(datasets.EVAL_DIR.glob("*.jsonl")):
            print(p.name)
        return 0
    if args.dataset != "gw1000":
        raise SystemExit(f"no builder for dataset {args.dataset!r} yet")
    out = datasets.build_gw1000(args.labels)
    items, _ = datasets.load("gw1000", args.labels)
    print(f"wrote {out} ({len(items)} items)")
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
