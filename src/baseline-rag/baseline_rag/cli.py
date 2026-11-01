"""gw-baseline: build, inspect, mirror and package the shared chunk store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from baseline_rag import chunks as chunk_store


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("gw-baseline", description="Chunk store for the hybrid baseline")
    ap.add_argument("action", choices=["build", "stats", "sample", "pg-import", "pg-check", "package"])
    ap.add_argument("--build-id", default=chunk_store.DEFAULT_BUILD)
    ap.add_argument("--db", type=Path, help="graph DuckDB holding the parsed statements")
    ap.add_argument("--n", type=int, default=3, help="chunks to print for `sample`")
    ap.add_argument("--unit", choices=chunk_store.UNITS, default="statement",
                    help="one chunk per statement (default), or passage windows of about 200 words")
    ap.add_argument("--reuse", help="build: take the vectors of identical chunks from this existing store")
    ap.add_argument("--dsn", help="Postgres connection string (default PG_DSN or the compose default)")
    ap.add_argument("--out", type=Path, help="zip path for `package`")
    ap.add_argument("--with-eval", action="store_true",
                    help="package: include the frozen human-gold evaluation snapshot under eval/")
    args = ap.parse_args(argv)

    if args.action in ("pg-import", "pg-check", "package"):
        from baseline_rag import pg

        if args.action == "pg-import":
            print(json.dumps(pg.import_store(args.build_id, args.dsn), indent=2))
        elif args.action == "pg-check":
            result = pg.check(args.build_id, args.dsn)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        else:
            print(json.dumps(pg.package(args.build_id, args.out, with_eval=args.with_eval), indent=2))
        return 0

    if args.action == "build":
        print(json.dumps(chunk_store.build(args.build_id, args.db, unit=args.unit, reuse=args.reuse),
                         indent=2))
        return 0
    chunks, vectors, manifest = chunk_store.load(args.build_id)
    if args.action == "stats":
        words = [len(c.text.split()) for c in chunks]
        print(json.dumps({**manifest, "embedding_shape": list(vectors.shape),
                          "words_per_chunk": {"min": min(words), "mean": sum(words) / len(words),
                                              "max": max(words)}}, indent=2))
        return 0
    for c in chunks[: args.n]:
        print(f"\n[{c.chunk_id}] {c.company} {c.year} p.{c.page} ({len(c.text.split())} words)")
        print(c.text[:400])
    return 0
