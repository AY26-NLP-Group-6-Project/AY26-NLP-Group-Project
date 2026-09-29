"""Rank-aware retrieval evaluation: P@K, R@K, MRR, nDCG@K, wrong-company@K.

The course brief asks for retrieval to be measured on its own, not only through downstream accuracy,
because retrieval caps everything after it. Judgements come from a **pooled** set: every configuration
contributes its top-k, the union is judged once by hand, and each configuration is then scored against
the same pool. Judging only one system's output would flatter it.

    gw-eval --task retrieval --system baseline-rag --queries queries.jsonl --export-pool pool.csv
    # ... annotators fill the `relevant` column (0/1, or 0-3 graded)
    gw-eval --task retrieval --system baseline-rag --queries queries.jsonl --qrels qrels.jsonl

Query file: one JSON object per line with `query_id`, `text`, and optionally `company`, `aspect`,
`anchor_year`, `year_from`, `year_to`, `condition`, `type` (the brief asks for a few query types).
Qrels file: `{"query_id": ..., "relevant": {"<doc_id>": 1, ...}}`, grades 0-3.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path

from gw_common.eval import metrics as M
from gw_common.schemas import EvidenceCondition, Query

DEFAULT_K = 10
QUERY_TYPES = ("company_claim", "cross_year_aspect", "generic")


def load_queries(path: Path) -> list[dict]:
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        q = json.loads(line)
        if "text" not in q:
            raise ValueError(f"{path}:{i}: query needs a `text` field")
        q.setdefault("query_id", str(i))
        q.setdefault("type", "generic")
        out.append(q)
    return out


def load_qrels(path: Path) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            out[str(record["query_id"])] = {str(k): int(v) for k, v in record["relevant"].items()}
    return out


def to_query(spec: dict, k: int) -> Query:
    condition = EvidenceCondition(spec.get("condition", EvidenceCondition.CROSS_YEAR_RRF.value))
    return Query(
        text=spec["text"], company=spec.get("company"), aspect=spec.get("aspect"),
        year_from=spec.get("year_from"), year_to=spec.get("year_to"),
        anchor_year=spec.get("anchor_year"), target_text=spec.get("target_text"),
        condition=condition,
    )


def run(retriever, queries: Sequence[dict], k: int = DEFAULT_K) -> dict[str, list]:
    """Retrieve for each query; returns query_id -> ranked spans."""
    return {q["query_id"]: retriever.retrieve(to_query(q, k), k=k) for q in queries}


def export_pool(results: dict[str, dict[str, list]], queries: Sequence[dict], out: Path) -> dict:
    """Union of every configuration's top-k, as a judging sheet (one row per query-document)."""
    by_id = {q["query_id"]: q for q in queries}
    rows, seen = [], set()
    for config, per_query in results.items():
        for query_id, spans in per_query.items():
            for rank, span in enumerate(spans, 1):
                key = (query_id, span.statement_id)
                if key in seen:
                    continue
                seen.add(key)
                q = by_id[query_id]
                rows.append({
                    "query_id": query_id, "query_type": q.get("type", ""), "query": q["text"][:300],
                    "company": q.get("company", ""), "doc_id": span.statement_id,
                    "doc_company": span.company, "doc_year": span.year, "doc_page": span.page,
                    "text": span.text[:600], "first_seen_config": config, "first_rank": rank,
                    "relevant": "",
                })
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["query_id"])
        writer.writeheader()
        writer.writerows(rows)
    return {"queries": len(by_id), "pooled_documents": len(rows), "configs": list(results), "out": str(out)}


def score(per_query: dict[str, list], qrels: dict[str, dict[str, int]], queries: Sequence[dict],
          k: int = DEFAULT_K) -> dict:
    """Mean rank-aware metrics over the queries that have judgements."""
    by_id = {q["query_id"]: q for q in queries}
    rows = []
    for query_id, spans in per_query.items():
        judged = qrels.get(query_id)
        if not judged:
            continue
        relevant = {doc for doc, grade in judged.items() if grade > 0}
        ranked = [s.statement_id for s in spans]
        expected = by_id.get(query_id, {}).get("company")
        rows.append({
            "query_id": query_id,
            "type": by_id.get(query_id, {}).get("type", "generic"),
            "p_at_5": M.precision_at_k(ranked, relevant, 5),
            "r_at_10": M.recall_at_k(ranked, relevant, 10),
            "mrr": M.mrr(ranked, relevant),
            "ndcg_at_10": M.ndcg_at_k(ranked, relevant, 10),
            "wrong_company_at_10": (
                M.wrong_company_at_k([s.company for s in spans], expected, 10) if expected else None
            ),
        })
    if not rows:
        raise ValueError("no query in the run has judgements; check the qrels file")

    def mean(key: str, subset: list[dict]) -> float | None:
        values = [r[key] for r in subset if r[key] is not None]
        return sum(values) / len(values) if values else None

    keys = ["p_at_5", "r_at_10", "mrr", "ndcg_at_10", "wrong_company_at_10"]
    out = {"judged_queries": len(rows), "k": k, "overall": {key: mean(key, rows) for key in keys}}
    out["by_type"] = {
        qtype: {"n": len(subset), **{key: mean(key, subset) for key in keys}}
        for qtype in sorted({r["type"] for r in rows})
        if (subset := [r for r in rows if r["type"] == qtype])
    }
    out["per_query"] = rows
    return out
