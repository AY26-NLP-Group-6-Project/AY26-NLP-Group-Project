"""gw-baseline: build and inspect the shared passage store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from baseline_rag import chunks as chunk_store


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("gw-baseline", description="Chunk store for the hybrid baseline")
    ap.add_argument("action", choices=["build", "stats", "sample"])
    ap.add_argument("--build-id", default="dev")
    ap.add_argument("--db", type=Path, help="graph DuckDB holding the parsed statements")
    ap.add_argument("--n", type=int, default=3, help="passages to print for `sample`")
    args = ap.parse_args(argv)

    if args.action == "build":
        print(json.dumps(chunk_store.build(args.build_id, args.db), indent=2))
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
