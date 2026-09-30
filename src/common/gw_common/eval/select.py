"""Choosing which items an experiment runs on: split, slices, sampling.

Kept apart from the runner so the CLI, the coming FastAPI layer and the query exporter all select
items the same way, and so a slice can be described in a manifest by the string that produced it.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence

from gw_common.schemas import GoldItem

# Slices an experiment can ask for by name. Each maps an item to a bucket, or to None to drop it.
SLICERS: dict[str, Callable[[GoldItem], object]] = {
    "split": lambda it: it.split,
    "row_type": lambda it: it.meta.get("row_type"),
    "aspect_source": lambda it: it.meta.get("aspect_source"),
    "category": lambda it: it.category or "(no aspect)",
    "company": lambda it: it.company,
    "year": lambda it: it.year,
    "pilot": lambda it: "pilot" if it.pilot else "main",
    "has_aspect": lambda it: "aspect" if it.aspect else "no_aspect",
    "gold": lambda it: it.gold_label.value,
    "agreement": lambda it: (
        None if it.meta.get("agreement") is None
        else "unanimous" if float(it.meta["agreement"]) >= 1.0 else "split"
    ),
    "aspect_weak": lambda it: "weak" if it.meta.get("aspect_weak") else "clear",
}


def parse_slices(spec: str | None) -> dict[str, set[str]]:
    """`row_type=aspect,category=workplace|management` -> {"row_type": {"aspect"}, ...}."""
    out: dict[str, set[str]] = {}
    for clause in (spec or "").split(","):
        clause = clause.strip()
        if not clause:
            continue
        key, _, values = clause.partition("=")
        key = key.strip()
        if key not in SLICERS:
            raise ValueError(f"unknown slice {key!r}; known: {', '.join(sorted(SLICERS))}")
        out[key] = {v.strip() for v in values.split("|") if v.strip()}
    return out


def select(
    items: Sequence[GoldItem],
    *,
    split: str | None = None,
    slices: dict[str, set[str]] | None = None,
    sample: int | None = None,
    limit: int | None = None,
    seed: int = 20260929,
) -> list[GoldItem]:
    chosen = list(items)
    if split and split != "all":
        chosen = [it for it in chosen if it.split == split]
    for key, values in (slices or {}).items():
        fn = SLICERS[key]
        chosen = [it for it in chosen if str(fn(it)) in values]
    if sample and sample < len(chosen):
        chosen = sorted(random.Random(seed).sample(chosen, sample), key=lambda it: int(it.item_id))
    if limit:
        chosen = chosen[:limit]
    return chosen


def describe(items: Sequence[GoldItem], keys: Sequence[str] = ("split", "row_type", "gold")) -> dict:
    out: dict[str, dict[str, int]] = {}
    for key in keys:
        fn = SLICERS[key]
        counts: dict[str, int] = {}
        for it in items:
            bucket = fn(it)
            if bucket is None:
                continue
            counts[str(bucket)] = counts.get(str(bucket), 0) + 1
        out[key] = dict(sorted(counts.items()))
    return out
