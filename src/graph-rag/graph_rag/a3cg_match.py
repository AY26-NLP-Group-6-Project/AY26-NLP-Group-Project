"""Recover report context for A3CG statements that also occur in our corpus.

A3CG releases isolated statements (2017–2022) without company, year or page. Some of them recur
verbatim in our 2020–2025 reports, because sustainability reports repeat paragraphs year to year. For
those we can attach provenance and neighbouring sentences and run the evidence conditions against
A3CG's own human labels.

Matching is conservative:
- normalised text equality, statements of at least MIN_TOKENS tokens (short ones match by accident);
- every match must belong to one company, otherwise the sentence is template text shared across
  issuers and its source is unknowable;
- the anchor is the earliest matching year inside A3CG's range (<= 2022) when there is one, else the
  earliest match. A later-year anchor is a proxy: the A3CG copy came from an earlier report we do not
  hold, whose wording was repeated.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from gw_common.datasets import A3CG_DIR, a3cg_items, write_snapshot
from gw_common.evidence import normalise

from graph_rag.config import GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore

MIN_TOKENS = 6
A3CG_LAST_YEAR = 2022
CONTEXT_SENTENCES = 2
DATASET_ID = "a3cg-matched"
FULL_FILES = ("full/full_train.json", "full/full_val.json", "full/full_test.json")


def _records(root: Path) -> list[dict]:
    recs = {}
    for rel in FULL_FILES:
        for r in json.loads((root / rel).read_text(encoding="utf-8")):
            recs[r["sentence_id"]] = r
    return list(recs.values())


def match(store: DuckDBGraphStore, records: list[dict]) -> tuple[dict[int, dict], dict]:
    wanted = {}
    for r in records:
        key = normalise(r["text"])
        if len(key.split()) >= MIN_TOKENS:
            wanted.setdefault(key, []).append(r["sentence_id"])
    hits = defaultdict(list)
    rows = store.con.execute(
        "SELECT stmt_id, sha256, company, year, page, idx, text FROM statements"
    ).fetchall()
    for stmt_id, sha, company, year, page, idx, text in rows:
        key = normalise(text)
        if key in wanted:
            hits[key].append({"stmt_id": stmt_id, "sha256": sha, "company": company, "year": year,
                              "page": page, "idx": idx})

    provenance, multi_company = {}, 0
    for key, matches in hits.items():
        if len({m["company"] for m in matches}) > 1:
            multi_company += 1
            continue
        in_range = [m for m in matches if m["year"] <= A3CG_LAST_YEAR]
        anchor = min(in_range or matches, key=lambda m: (m["year"], m["idx"]))
        prev, nxt = _neighbours(store, anchor["sha256"], anchor["idx"])
        for sid in wanted[key]:
            provenance[sid] = {
                "company": anchor["company"], "year": anchor["year"], "page": anchor["page"],
                "file": anchor["sha256"], "context_prev": prev, "context_next": nxt,
                "anchor_in_a3cg_range": bool(in_range),
            }
    info = {
        "a3cg_statements": len(records),
        "eligible_statements": sum(len(v) for v in wanted.values()),
        "matched_texts": len(hits),
        "dropped_multi_company": multi_company,
        "kept_statements": len(provenance),
        "anchor_in_a3cg_range": sum(p["anchor_in_a3cg_range"] for p in provenance.values()),
    }
    return provenance, info


def _neighbours(store: DuckDBGraphStore, sha: str, idx: int) -> tuple[str, str]:
    rows = store.con.execute(
        "SELECT idx, text FROM statements WHERE sha256 = ? AND idx BETWEEN ? AND ? ORDER BY idx",
        [sha, idx - CONTEXT_SENTENCES, idx + CONTEXT_SENTENCES],
    ).fetchall()
    prev = " ".join(t for i, t in rows if i < idx)
    nxt = " ".join(t for i, t in rows if i > idx)
    return prev, nxt


def export(cfg: GraphConfig, root: Path | None = None) -> dict:
    records = _records(root or A3CG_DIR)
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        provenance, info = match(store, records)
    kept = [r for r in records if r["sentence_id"] in provenance]
    items, skipped = a3cg_items(kept, provenance)
    path = write_snapshot(DATASET_ID, "a3cg_gold", items, replace=True)
    return {**info, "items": len(items), "multi_action_skipped": skipped,
            "action_items": sum(it.aspect is not None for it in items), "snapshot": path.name}
