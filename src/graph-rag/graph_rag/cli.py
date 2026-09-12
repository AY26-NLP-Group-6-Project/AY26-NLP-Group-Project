"""gw-graph: build stages for the temporal claim graph (M1-M3)."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("gw-graph")
    ap.add_argument("stage", choices=["parse", "aspects", "canonical", "measures", "derive", "build"])
    ap.add_argument("--config", default="configs/graph.dev.yaml")
    args = ap.parse_args(argv)
    raise SystemExit(f"stage {args.stage!r} not implemented yet (M1-M3); config={args.config}")
