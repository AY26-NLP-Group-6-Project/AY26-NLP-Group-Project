"""Stage 1: companies, reports and statements.

Deterministic: everything here comes from `kb/manifest.csv` and the PDF text, with no model in the
loop. Scope is set in the config: the companies the eval set touches, or every kept report.
"""

from __future__ import annotations

import csv
import json

import pymupdf

from graph_rag.build.text import clean_page, normalise, split_sentences
from graph_rag.config import KB_DIR, GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore

MANIFEST = KB_DIR / "manifest.csv"


def eval_snapshot(cfg: GraphConfig) -> list[dict]:
    from gw_common import datasets

    items, _ = datasets.load(cfg.dataset_id, cfg.label_source)
    return [i.model_dump() for i in items]


def scoped_reports(cfg: GraphConfig, eval_files: set[str]) -> list[dict]:
    rows = [r for r in csv.DictReader(MANIFEST.open(encoding="utf-8")) if r["doc_status"] == "kept"]
    lo, hi = cfg.years
    in_years = [r for r in rows if lo <= int(r["year"]) <= hi]
    if cfg.scope == "all":          # the retrieval corpus is the whole KB, not just eval companies
        return in_years
    companies = {r["company"] for r in rows if r["file"] in eval_files}
    return [r for r in in_years if r["company"] in companies]


def stmt_id(sha256: str, page: int, idx: int) -> str:
    return f"{sha256[:8]}p{page:04d}s{idx:03d}"


def run(cfg: GraphConfig, store: DuckDBGraphStore, verbose: bool = True, rebuild: bool = False) -> dict:
    items = eval_snapshot(cfg)
    reports = scoped_reports(cfg, {i["file"] for i in items})
    if rebuild:
        store.clear("statements", "reports", "companies")

    companies = {(r["company"], r["sgx_code"] or None) for r in reports}
    store.insert_many("companies", sorted(companies), 2)
    store.insert_many(
        "reports",
        [(r["sha256"], r["company"], int(r["year"]), r["file"], int(r["pages"])) for r in reports],
        5,
    )

    done = {
        row[0]
        for row in store.con.execute("SELECT DISTINCT sha256 FROM statements").fetchall()
    }
    todo = [r for r in reports if r["sha256"] not in done]
    if verbose and done:
        print(f"  resuming: {len(done)} reports already parsed, {len(todo)} to go")

    n_stmt = 0
    for n, r in enumerate(todo, 1):
        pdf = KB_DIR / r["file"]
        rows = []
        with pymupdf.open(pdf) as doc:
            for pno, page in enumerate(doc, 1):
                for idx, sent in enumerate(split_sentences(clean_page(page.get_text()))):
                    rows.append(
                        (
                            stmt_id(r["sha256"], pno, idx),
                            r["sha256"],
                            r["company"],
                            int(r["year"]),
                            pno,
                            idx,
                            sent,
                            normalise(sent),
                            "corpus",
                        )
                    )
        store.insert_many("statements", rows, 9)
        n_stmt += len(rows)
        rows.clear()
        if n % 10 == 0:
            store.checkpoint()          # keep the WAL bounded
        if verbose and n % 10 == 0:
            print(f"  parsed {n}/{len(todo)} reports, {n_stmt} statements", flush=True)
    store.checkpoint()

    total = store.con.execute("SELECT count(*) FROM statements").fetchone()[0]
    stats = {"reports": len(reports), "companies": len(companies),
             "statements_added": n_stmt, "statements_total": total}
    (cfg.out_dir / "parse_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
