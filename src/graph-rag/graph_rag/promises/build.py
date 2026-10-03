"""From extracted targets to promises: one commitment, followed across the reports that state it.

Reports repeat their targets year after year, so the same commitment is extracted several times. A
*promise* merges those restatements: same company, same deadline year, same quantity, and metric names
that share most of their content words. The earliest statement is its origin.

A promise is **checkable** inside the corpus when

- it was stated before its deadline (origin report year < target year), so it was a commitment and not
  a result dressed as one;
- the deadline has passed inside the corpus window (target year <= the last corpus year) and the
  company published a report for the deadline year or later, where the outcome should appear;
- its metric names something (bare anaphors such as "this target" or "both indexes" are kept but
  flagged, because nothing can be looked up for them).

Targets of the same company on a similar metric but with a *different* deadline or quantity are not
merged; they are linked as `related`, which is what a moved goalpost looks like.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from gw_common.text import tokens

from graph_rag.config import GraphConfig
from graph_rag.promises.extract import out_dir
from graph_rag.store.duckdb_store import DuckDBGraphStore

MERGE_JACCARD = 0.5
VAGUE = {"target", "targets", "goal", "goals", "index", "indexes", "indices", "both", "this", "these",
         "such", "above", "performance", "same", "following", "commitment", "commitments", "objectives"}


def metric_key(metric: str) -> frozenset[str]:
    return frozenset(tokens(metric, min_len=2))


def is_vague(metric: str) -> bool:
    key = metric_key(metric)
    return not key or key <= VAGUE


def _similar(a: frozenset[str], b: frozenset[str]) -> bool:
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= MERGE_JACCARD


def _same_quantity(a: float | None, b: float | None) -> bool:
    """A restatement often drops or adds the number ("all suppliers" vs "100% of suppliers"), so a
    missing quantity matches any; two stated quantities must be equal."""
    return a is None or b is None or a == b


def load_targets(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def consolidate(targets: list[dict]) -> list[dict]:
    """Merge restatements into promises. Deterministic: targets are visited in (company, year, id) order."""
    by_company: dict[str, list[dict]] = defaultdict(list)
    for t in sorted(targets, key=lambda t: (t["company"], t["year"], t["target_id"])):
        by_company[t["company"]].append(t)

    promises: list[dict] = []
    for company, items in by_company.items():
        groups: list[dict] = []
        for t in items:
            key = metric_key(t["metric"])
            home = next(
                (g for g in groups
                 if g["target_year"] == t["target_year"] and _same_quantity(g["quantity"], t["quantity"])
                 and _similar(g["key"], key)),
                None,
            )
            if home is None:
                home = {"key": key, "target_year": t["target_year"], "quantity": t["quantity"], "members": []}
                groups.append(home)
            elif home["quantity"] is None:
                home["quantity"] = t["quantity"]
            home["members"].append(t)
        for g in groups:
            origin = g["members"][0]
            years = sorted({m["year"] for m in g["members"]})
            promises.append({
                "promise_id": f"P{len(promises) + 1:05d}",
                "company": company,
                "metric": origin["metric"],
                "metric_vague": is_vague(origin["metric"]),
                "category": origin["category"],
                "kind": origin["kind"],
                "direction": origin["direction"],
                "quantity": g["quantity"],
                "unit": next((m["unit"] for m in g["members"] if m["unit"]), None),
                "baseline_year": origin["baseline_year"],
                "target_year": origin["target_year"],
                "recurring": any(m["recurring"] for m in g["members"]),
                "origin": {k: origin[k] for k in ("target_id", "stmt_id", "year", "page", "file", "text",
                                                  "target_text")},
                "stated_in_years": years,
                "restatements": [{"target_id": m["target_id"], "year": m["year"], "page": m["page"]}
                                 for m in g["members"][1:]],
                "_key": g["key"],
            })
    # moved goalposts: same company, similar metric, different deadline or quantity
    by_co: dict[str, list[dict]] = defaultdict(list)
    for p in promises:
        by_co[p["company"]].append(p)
    for group in by_co.values():
        for p in group:
            p["related"] = [
                {"promise_id": q["promise_id"], "target_year": q["target_year"], "quantity": q["quantity"],
                 "first_stated": q["origin"]["year"]}
                for q in group
                if q is not p and _similar(p["_key"], q["_key"])
                and (q["target_year"] != p["target_year"]
                     or not _same_quantity(q["quantity"], p["quantity"]))
            ]
    for p in promises:
        del p["_key"]
    return promises


def mark_checkable(promises: list[dict], report_years: dict[str, set[int]], last_year: int) -> None:
    for p in promises:
        years = report_years.get(p["company"], set())
        window = sorted(y for y in years if p["target_year"] <= y <= p["target_year"] + 1)
        reasons = []
        if p["origin"]["year"] >= p["target_year"]:
            reasons.append("stated_in_or_after_deadline_year")
        if p["target_year"] > last_year:
            reasons.append("deadline_after_corpus")
        elif not window:
            reasons.append("no_report_for_deadline_year")
        if p["metric_vague"]:
            reasons.append("vague_metric")
        p["outcome_years"] = window
        p["checkable"] = not reasons
        p["not_checkable_because"] = reasons


def build(cfg: GraphConfig, source: str | None = None) -> dict:
    """`source` picks `targets.<source>.jsonl` (an outside extractor's validated output); the default is
    the in-repo extractor's `targets.jsonl`. Which one was used is recorded in the stats."""
    base = out_dir(cfg)
    targets_path = base / (f"targets.{source}.jsonl" if source else "targets.jsonl")
    targets = load_targets(targets_path)
    promises = consolidate(targets)
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        report_years: dict[str, set[int]] = defaultdict(set)
        for company, year in store.con.execute("SELECT company, year FROM reports").fetchall():
            report_years[company].add(year)
    mark_checkable(promises, report_years, last_year=cfg.years[1])
    with (base / "promises.jsonl").open("w", encoding="utf-8") as f:
        for p in promises:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    checkable = [p for p in promises if p["checkable"]]
    reasons = Counter(r for p in promises for r in p["not_checkable_because"])
    stats = {
        "targets_file": targets_path.name,
        "targets": len(targets),
        "promises": len(promises),
        "restated_promises": sum(len(p["stated_in_years"]) > 1 for p in promises),
        "with_related_variant": sum(bool(p["related"]) for p in promises),
        "checkable": len(checkable),
        "checkable_companies": len({p["company"] for p in checkable}),
        "checkable_by_kind": dict(Counter(p["kind"] for p in checkable)),
        "checkable_by_target_year": dict(sorted(Counter(p["target_year"] for p in checkable).items())),
        "checkable_recurring": sum(p["recurring"] for p in checkable),
        "not_checkable_reasons": dict(reasons),
        "out": str(base / "promises.jsonl"),
    }
    (base / "promises_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
