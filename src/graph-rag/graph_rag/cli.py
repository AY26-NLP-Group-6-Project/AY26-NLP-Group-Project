"""gw-graph: build and inspect the temporal claim graph."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from graph_rag import extract as extraction
from graph_rag.build import aspects as stage_aspects
from graph_rag.build import derive as stage_derive
from graph_rag.build import parse as stage_parse
from graph_rag.config import REPO_ROOT, GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore

STAGES = {"parse": stage_parse.run, "aspects": stage_aspects.run, "derive": stage_derive.run}


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def build(
    cfg: GraphConfig, stages: list[str], rebuild: bool = False, extracted: str | None = None
) -> dict:
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    stats = {}
    with DuckDBGraphStore(cfg.db_path) as store:
        for name in stages:
            print(f"[{name}]", flush=True)
            kwargs: dict = {}
            if name == "parse":
                kwargs["rebuild"] = rebuild
            elif name == "aspects" and extracted:
                kwargs["extracted"] = extracted
            stats[name] = STAGES[name](cfg, store, **kwargs)
        counts = store.counts()
        chains = store.chains(min_years=2)
    manifest = {
        "build_id": cfg.build_id,
        "config": asdict(cfg),
        "config_hash": cfg.hash(),
        "git_sha": _git_sha(),
        "built_at": datetime.now(UTC).isoformat(),
        "wall_seconds": round(time.perf_counter() - t0, 1),
        "stages": stats,
        "counts": counts,
        "cross_year_chains": len(chains),
    }
    (cfg.out_dir / "build_manifest.json").write_text(json.dumps(manifest, indent=2, default=str),
                                                     encoding="utf-8")
    return manifest


def stats(cfg: GraphConfig, top: int = 15) -> None:
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        counts = store.counts()
        chains = store.chains(min_years=2)
    print(json.dumps(counts, indent=2))
    print(f"cross-year chains (>=2 years): {len(chains)}")
    print(f"chains spanning >=3 years:     {sum(len(c.years) >= 3 for c in chains)}")
    for c in chains[:top]:
        print(f"  {c.company:28.28s} {c.canonical:38.38s} {c.years}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("gw-graph")
    ap.add_argument(
        "stage",
        choices=[*STAGES, "build", "stats", "export-extract", "export-gold", "score-extraction"],
    )
    ap.add_argument("--config", default="configs/graph.dev.yaml")
    ap.add_argument("--build-id")
    ap.add_argument("--rebuild", action="store_true", help="drop parsed statements and start over")
    ap.add_argument("--out", help="output path for export-* stages")
    ap.add_argument("--pred", help="extractor output JSONL for score-extraction")
    ap.add_argument("--gold", help="gold JSONL for score-extraction (default data/eval/extract_gold.jsonl)")
    ap.add_argument("--limit", type=int, help="cap the number of exported statements")
    ap.add_argument("--per-report", type=int, help="sample at most N statements per report")
    ap.add_argument("--extracted", help="extractor output JSONL to ingest during the aspects stage")
    args = ap.parse_args(argv)

    cfg = GraphConfig.load(args.config, build_id=args.build_id)
    if args.stage == "stats":
        stats(cfg)
        return 0
    if args.stage == "export-extract":
        out = Path(args.out or cfg.out_dir / "extract_input.jsonl")
        print(json.dumps(extraction.export_input(cfg, out, args.limit, args.per_report), indent=2))
        return 0
    if args.stage == "export-gold":
        out = Path(args.out or REPO_ROOT / "data" / "eval" / "extract_gold.jsonl")
        print(json.dumps(extraction.export_gold(out), indent=2))
        return 0
    if args.stage == "score-extraction":
        if not args.pred:
            ap.error("--pred is required for score-extraction")
        gold = Path(args.gold or REPO_ROOT / "data" / "eval" / "extract_gold.jsonl")
        result = extraction.score(Path(args.pred), gold)
        print(json.dumps(result, indent=2))
        out = cfg.out_dir / "extraction_score.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 0 if result["gate"]["passed"] else 1
    stages = list(STAGES) if args.stage == "build" else [args.stage]
    manifest = build(cfg, stages, rebuild=args.rebuild, extracted=args.extracted)
    print(json.dumps({k: manifest[k] for k in ("counts", "cross_year_chains", "wall_seconds")}, indent=2))
    return 0
