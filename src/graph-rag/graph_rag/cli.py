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
from graph_rag.build import canonical as stage_canonical
from graph_rag.build import derive as stage_derive
from graph_rag.build import parse as stage_parse
from graph_rag.config import REPO_ROOT, GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore

STAGES = {
    "parse": stage_parse.run,
    "aspects": stage_aspects.run,
    "canonical": stage_canonical.run,
    "derive": stage_derive.run,
}


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def build(
    cfg: GraphConfig,
    stages: list[str],
    rebuild: bool = False,
    extracted: str | None = None,
    canon_kwargs: dict | None = None,
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
            elif name == "canonical":
                kwargs.update(canon_kwargs or {"method": "exact"})
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
        choices=[*STAGES, "build", "stats", "export-extract", "export-gold", "score-extraction",
                 "canon-pools", "canon-tune", "canon-verify", "canon-spotcheck", "canon-spotcheck-score",
                 "export-a3cg"],
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
    ap.add_argument("--method", choices=stage_canonical.METHODS, default="exact",
                    help="canonicalisation method for the canonical stage")
    ap.add_argument("--threshold", type=float, help="cosine similarity threshold for --method hac")
    ap.add_argument("--labels", help="annotated pool partitions JSONL for canon-tune / canon-verify")
    ap.add_argument("--split", choices=["val", "test"], default="val")
    ap.add_argument("--variant", choices=["rules", "rules+demos"], default="rules")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--floor", type=float, default=0.70)
    ap.add_argument("--pools", help="pool file for canon-tune / canon-verify (default canon_pools.jsonl)")
    ap.add_argument("--n-pools", type=int, default=60)
    ap.add_argument("--exclude-pools", nargs="*", default=[], help="pool files whose forms must not reappear")
    ap.add_argument("--all-split", choices=["val", "test"], help="assign every exported pool to this split")
    ap.add_argument("--prefix", default="pool")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--sheet", help="returned spot-check CSV for canon-spotcheck-score")
    args = ap.parse_args(argv)

    cfg = GraphConfig.load(args.config, build_id=args.build_id)
    if args.stage == "stats":
        stats(cfg)
        return 0
    if args.stage == "export-extract":
        out = Path(args.out or cfg.out_dir / "extract_input.jsonl")
        print(json.dumps(extraction.export_input(cfg, out, args.limit, args.per_report), indent=2))
        return 0
    if args.stage == "export-a3cg":
        from graph_rag import a3cg_match

        print(json.dumps(a3cg_match.export(cfg), indent=2))
        return 0
    if args.stage == "export-gold":
        out = Path(args.out or REPO_ROOT / "data" / "eval" / "extract_gold.jsonl")
        print(json.dumps(extraction.export_gold(out), indent=2))
        return 0
    if args.stage == "canon-pools":
        from graph_rag.canonical import tuning

        out = Path(args.out or cfg.out_dir / "canon_pools.jsonl")
        info = tuning.export_pools(cfg, out, n_pools=args.n_pools,
                                   exclude_pools=[Path(x) for x in args.exclude_pools],
                                   split=args.all_split, prefix=args.prefix, seed=args.seed)
        print(json.dumps(info, indent=2))
        return 0
    if args.stage == "canon-tune":
        from graph_rag.canonical import tuning

        if not args.labels:
            ap.error("--labels is required for canon-tune")
        pools = Path(args.pools or cfg.out_dir / "canon_pools.jsonl")
        result = tuning.tune(cfg, pools, Path(args.labels))
        print(json.dumps(result["summary"], indent=2))
        return 0
    if args.stage == "canon-spotcheck":
        from graph_rag.build.canonical import load_phrases
        from graph_rag.canonical import spotcheck
        from graph_rag.canonical.embed import PhraseEmbedder
        from graph_rag.canonical.goldset import form_id

        if not (args.pools and args.labels):
            ap.error("--pools and --labels are required for canon-spotcheck")
        with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
            phrases, _, _ = load_phrases(store)
        vectors = PhraseEmbedder().embed([p.key for p in phrases])
        by_form = {form_id(p): vectors[i] for i, p in enumerate(phrases)}
        out = Path(args.out or cfg.out_dir / "spotcheck")
        info = spotcheck.export(Path(args.pools), Path(args.labels), by_form, out, k=args.k, floor=args.floor)
        print(json.dumps(info, indent=2))
        return 0
    if args.stage == "canon-spotcheck-score":
        from graph_rag.canonical import spotcheck

        out = Path(args.out or cfg.out_dir / "spotcheck")
        sheet = Path(args.sheet or out / "canon_spotcheck_pairs.csv")
        print(json.dumps(spotcheck.score(sheet, out / "canon_spotcheck_key.json"), indent=2))
        return 0
    if args.stage == "canon-verify":
        from graph_rag.canonical import tuning

        if not args.labels:
            ap.error("--labels is required for canon-verify")
        pools = Path(args.pools or cfg.out_dir / "canon_pools.jsonl")
        r = tuning.verify_eval(cfg, pools, Path(args.labels), args.split, args.variant, args.k, args.floor)
        pw = r["metrics"]["pairwise"]
        print(json.dumps({k: r[k] for k in ("split", "variant", "candidates", "gold_pairs",
                                            "gold_pairs_among_candidates", "verifier_confusion", "usage")},
                         indent=2))
        print(f"pairwise P {pw['precision']:.3f}  R {pw['recall']:.3f}  F1 {pw['f1']:.3f}  "
              f"F0.5 {r['pairwise_f05']:.3f}")
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
    canon_kwargs = {"method": args.method, "threshold": args.threshold}
    manifest = build(
        cfg, stages, rebuild=args.rebuild, extracted=args.extracted, canon_kwargs=canon_kwargs
    )
    print(json.dumps({k: manifest[k] for k in ("counts", "cross_year_chains", "wall_seconds")}, indent=2))
    return 0
