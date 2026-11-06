"""Rank-aware retrieval evaluation: P@K, R@K, MRR, nDCG@K, wrong-company@K.

The course brief asks for retrieval to be measured on its own, not only through downstream accuracy,
because retrieval caps everything after it. Judgements come from a **pooled** set: every configuration
contributes its top-k, the union is judged once, and each configuration is then scored against the same
pool. Judging only one system's output would flatter it.

    gw-eval --task retrieval --build-queries queries.jsonl --split dev
    gw-eval --task retrieval --system baseline-rag --queries queries.jsonl \
            --modes bm25,dense,rrf,rrf+rerank,graph-rag:graph,graph-rag:fused --export-pool pool.csv
    # a person fills the `relevant` column (0-3), or the model grades the pool:
    gw-eval --task retrieval --judge-pool pool.csv --queries queries.jsonl --qrels qrels.jsonl
    gw-eval --task retrieval --system baseline-rag --queries queries.jsonl --modes ... --qrels qrels.jsonl

Query file: one JSON object per line with `query_id`, `text`, and optionally `company`, `aspect`,
`anchor_year`, `year_from`, `year_to`, `condition`, `type` (the brief asks for a few query types).
Qrels file: `{"query_id": ..., "relevant": {"<doc_id>": 1, ...}}`, grades 0-3.

A mode is a configuration of `--system` (`bm25`, `dense`, `rrf`, `rrf+rerank` for the hybrid baseline),
or `<system>:<mode>` for another system; `graph` and `fused` name the graph system's two conditions.
Scoring writes a run directory under `artifacts/runs/` that `--publish` accepts.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from gw_common.eval import metrics as M
from gw_common.eval.runner import RUNS_DIR, _git, new_run_dir
from gw_common.schemas import EvidenceCondition, GoldItem, Query

DEFAULT_K = 10
DEFAULT_MIN_GRADE = 2
SEED = 20260912
QUERY_TYPES = ("company_claim", "cross_year_aspect", "generic")
# How many queries of each type `build_queries` draws from the development split.
QUERY_PLAN = {"company_claim": 30, "cross_year_aspect": 30, "generic": 20}
# Modes that name a condition rather than a baseline mode: the graph system's two arms.
CONDITION_MODES = {"graph": EvidenceCondition.CROSS_YEAR_GRAPH, "fused": EvidenceCondition.CROSS_YEAR_FUSED}
REFERENCE_MODE = "rrf+rerank"
METRIC_KEYS = ("p_at_5", "r_at_10", "mrr", "ndcg_at_10", "wrong_company_at_10")

# Topic queries over every company, written by the group (not by annotators) to cover the A3CG
# categories: emissions, energy, water, waste, biodiversity, workplace, safety, governance, data,
# supply chain, buildings, climate disclosure, community, customers, targets.
GENERIC_QUERIES = (
    "commitment to achieve net zero emissions by 2050",
    "Scope 3 greenhouse gas emissions measurement and reporting",
    "renewable energy share of total electricity consumption",
    "solar panel installation on rooftops",
    "water consumption reduction target",
    "waste recycling rate and recycling initiatives",
    "single-use plastics reduction",
    "biodiversity conservation and tree planting",
    "gender diversity on the board of directors",
    "employee training hours per employee target",
    "workplace injury rate and lost-time incidents",
    "anti-corruption policy and whistle-blowing channel",
    "data privacy and cybersecurity incidents",
    "supplier code of conduct and supply chain due diligence",
    "green building certification such as BCA Green Mark",
    "TCFD-aligned climate risk disclosure",
    "energy intensity reduction per unit of revenue",
    "community investment and volunteering hours",
    "customer satisfaction survey results",
    "science-based targets validated by SBTi",
)


# ------------------------------------------------------------------------------------------ queries
def build_queries(items: Sequence[GoldItem], *, seed: int = SEED,
                  plan: dict[str, int] | None = None) -> list[dict]:
    """Three query types from the development items, seeded, no gold label read.

    `company_claim`: a dev sentence with its company and aspect, the RQ1 cross-year question (its own
    report year excluded); `cross_year_aspect`: one (company, aspect) pair as a short query over every
    year of the company; `generic`: the topic queries above over the whole store. Only items with an
    A3CG category are drawn, so the aspect asked about is one the annotators accepted.
    """
    plan = {**QUERY_PLAN, **(plan or {})}
    rng = random.Random(seed)
    usable = sorted((it for it in items if it.aspect and it.category and it.company and it.year and it.text),
                    key=lambda it: it.item_id)
    claims = rng.sample(usable, min(plan["company_claim"], len(usable)))
    taken = {it.item_id for it in claims}
    pairs: dict[tuple[str, str], GoldItem] = {}
    for it in usable:
        if it.item_id not in taken:
            pairs.setdefault((it.company, it.aspect.strip().lower()), it)
    aspects = rng.sample(sorted(pairs.values(), key=lambda it: it.item_id),
                         min(plan["cross_year_aspect"], len(pairs)))
    out = [{
        "query_id": f"c-{it.item_id}", "type": "company_claim", "text": it.text, "company": it.company,
        "aspect": it.aspect, "anchor_year": it.year, "target_text": it.text,
        "condition": EvidenceCondition.CROSS_YEAR_RRF.value, "item_id": it.item_id, "category": it.category,
    } for it in claims]
    out += [{
        "query_id": f"a{i:02d}", "type": "cross_year_aspect", "text": it.aspect, "company": it.company,
        "aspect": it.aspect, "condition": EvidenceCondition.CROSS_YEAR_RRF.value, "item_id": it.item_id,
        "category": it.category,
    } for i, it in enumerate(aspects, 1)]
    out += [{"query_id": f"g{i:02d}", "type": "generic", "text": text,
             "condition": EvidenceCondition.CROSS_YEAR_RRF.value}
            for i, text in enumerate(GENERIC_QUERIES[: plan["generic"]], 1)]
    return out


def write_queries(queries: Sequence[dict], path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in queries), encoding="utf-8")
    counts = {t: sum(q["type"] == t for q in queries) for t in QUERY_TYPES}
    return {"queries": len(queries), "by_type": counts, "out": str(path)}


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


def to_query(spec: dict, k: int, condition: EvidenceCondition | None = None) -> Query:
    default = EvidenceCondition.CROSS_YEAR_RRF.value
    condition = condition or EvidenceCondition(spec.get("condition", default))
    return Query(
        text=spec["text"], company=spec.get("company"), aspect=spec.get("aspect"),
        year_from=spec.get("year_from"), year_to=spec.get("year_to"),
        anchor_year=spec.get("anchor_year"), target_text=spec.get("target_text"),
        condition=condition,
    )


def parse_mode(spec: str, default_system: str | None) -> tuple[str, str, EvidenceCondition | None]:
    """`bm25` -> (default system, 'bm25', None);
    `graph-rag:graph` -> ('graph-rag', 'graph', CROSS_YEAR_GRAPH)."""
    system, _, mode = spec.rpartition(":")
    system = system or default_system
    if not system:
        raise ValueError(f"mode {spec!r} needs a system: give --system or write <system>:<mode>")
    return system, mode, CONDITION_MODES.get(mode)


def run(retriever, queries: Sequence[dict], k: int = DEFAULT_K,
        condition: EvidenceCondition | None = None) -> dict[str, list]:
    """Retrieve for each query; returns query_id -> ranked spans. `condition` overrides the query's."""
    return {q["query_id"]: retriever.retrieve(to_query(q, k, condition), k=k) for q in queries}


# --------------------------------------------------------------------------------------------- pool
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


# -------------------------------------------------------------------------------------------- score
def score(per_query: dict[str, list], qrels: dict[str, dict[str, int]], queries: Sequence[dict],
          k: int = DEFAULT_K, min_grade: int = DEFAULT_MIN_GRADE) -> dict:
    """Mean rank-aware metrics over the queries that have judgements; relevant means grade >= min_grade."""
    by_id = {q["query_id"]: q for q in queries}
    rows = []
    for query_id, spans in per_query.items():
        judged = qrels.get(query_id)
        if not judged:
            continue
        relevant = {doc for doc, grade in judged.items() if grade >= min_grade}
        ranked = [s.statement_id for s in spans]
        expected = by_id.get(query_id, {}).get("company")
        rows.append({
            "query_id": query_id,
            "type": by_id.get(query_id, {}).get("type", "generic"),
            "returned": len(ranked),
            "relevant_in_pool": len(relevant),
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

    keys = [*METRIC_KEYS, "returned", "relevant_in_pool"]
    out = {"judged_queries": len(rows), "k": k, "min_grade": min_grade,
           "overall": {key: mean(key, rows) for key in keys}}
    out["by_type"] = {
        qtype: {"n": len(subset), **{key: mean(key, subset) for key in keys}}
        for qtype in sorted({r["type"] for r in rows})
        if (subset := [r for r in rows if r["type"] == qtype])
    }
    out["per_query"] = rows
    return out


def paired_bootstrap(a: Sequence[float], b: Sequence[float], n: int = 2000, seed: int = SEED) -> dict:
    """Mean of b - a over the same queries with a bootstrap 95% interval; wins are queries where b > a."""
    diffs = np.asarray(b, dtype=float) - np.asarray(a, dtype=float)
    rng = np.random.default_rng(seed)
    means = [float(diffs[rng.integers(0, len(diffs), len(diffs))].mean()) for _ in range(n)]
    low, high = float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
    return {"mean": float(diffs.mean()), "ci95": [low, high],
            "wins": int((diffs > 0).sum()), "losses": int((diffs < 0).sum()), "n": int(len(diffs))}


def compare_configs(scores: dict[str, dict], reference: str, metric: str = "ndcg_at_10",
                    types: Sequence[str] | None = None) -> dict[str, dict]:
    """Each configuration against the reference on the queries both scored (optionally of some types)."""
    ref = {r["query_id"]: r for r in scores[reference]["per_query"]}
    out = {}
    for config, block in scores.items():
        if config == reference:
            continue
        pairs = [(ref[r["query_id"]][metric], r[metric]) for r in block["per_query"]
                 if r["query_id"] in ref and (types is None or r["type"] in types)]
        if pairs:
            out[config] = {"metric": metric, "reference": reference,
                           **paired_bootstrap([p[0] for p in pairs], [p[1] for p in pairs])}
    return out


# ---------------------------------------------------------------------------------------------- run
def _fmt(v, spec: str = ".3f") -> str:
    return "—" if v is None else format(v, spec)


def report_md(run_id: str, manifest: dict, scores: dict[str, dict], lenient: dict[str, dict],
              comparisons: dict[str, dict], judge_info: dict) -> str:
    cfg = manifest["config"]
    lines = [f"# {run_id}", "",
             "> **Model-judged relevance.** The pooled judgements were made by a model under "
             f"`{judge_info.get('prompt', 'a hand-made sheet')}`"
             + (f" ({judge_info.get('model')})" if judge_info.get("model") else "")
             + "; no human has graded this pool. Read the numbers as a comparison between "
             "configurations under one judge, not as absolute retrieval quality.", "",
             f"- task: `retrieval` · queries: `{cfg['queries']}` ({manifest['n_items']}; "
             + ", ".join(f"{t} {n}" for t, n in cfg["query_counts"].items()) + ")",
             f"- qrels: `{cfg['qrels']}` · pooled documents judged: {cfg['pool']['documents']} · "
             f"relevant at grade ≥ {cfg['min_grade']}: {cfg['pool']['relevant']} "
             f"(≥ 1: {cfg['pool']['relevant_lenient']})",
             f"- k = {cfg['k']} · configurations: " + ", ".join(f"`{c}`" for c in scores),
             f"- git: `{manifest['git_sha'][:8]}`{' (dirty)' if manifest.get('git_dirty') else ''}", ""]

    def table(title: str, pick) -> None:
        lines.extend([f"## {title}", "",
                      "| configuration | n | returned | P@5 | R@10 | MRR | nDCG@10 | wrong-company@10 "
                      "| nDCG@10 (grade ≥ 1) |",
                      "|---|---|---|---|---|---|---|---|---|"])
        for config, block in scores.items():
            b = pick(block)
            if not b:
                continue
            le = pick(lenient[config]) or {}
            lines.append(f"| `{config}` | {b.get('n', block['judged_queries'])} "
                         f"| {_fmt(b['returned'], '.1f')} | {_fmt(b['p_at_5'])} | {_fmt(b['r_at_10'])} "
                         f"| {_fmt(b['mrr'])} | {_fmt(b['ndcg_at_10'])} | {_fmt(b['wrong_company_at_10'])} "
                         f"| {_fmt(le.get('ndcg_at_10'))} |")
        lines.append("")

    table("All queries", lambda b: b["overall"])
    for qtype in QUERY_TYPES:
        if any(qtype in b["by_type"] for b in scores.values()):
            table(f"Queries of type `{qtype}`", lambda b, t=qtype: b["by_type"].get(t))
    if comparisons:
        lines.extend([f"## Against `{cfg['reference']}` (nDCG@10, paired over the same queries)", "",
                      "| configuration | queries | Δ mean | 95% CI | wins / losses |",
                      "|---|---|---|---|---|"])
        for config, c in comparisons.items():
            lines.append(f"| `{config}` | {c['n']} | {c['mean']:+.3f} "
                         f"| {c['ci95'][0]:+.3f} … {c['ci95'][1]:+.3f} | {c['wins']} / {c['losses']} |")
        lines.append("")
    lines.append("Pooled recall: the relevant set of a query is every pooled document at or above the grade, "
                 "so R@10 is recall against the union of the configurations compared, not against the "
                 "store. A configuration that returns nothing for a query type (the graph arms need a "
                 "company) scores 0 on those queries; read it on the types it serves.")
    return "\n".join(lines) + "\n"


def write_run(results: dict[str, dict[str, list]], queries: Sequence[dict], qrels: dict[str, dict[str, int]],
              *, queries_path: Path, qrels_path: Path, k: int = DEFAULT_K, min_grade: int = DEFAULT_MIN_GRADE,
              reference: str | None = None, retrievers: dict[str, dict] | None = None,
              judge_info: dict | None = None, out_root: Path | None = None) -> Path:
    """Score every configuration and write a run directory `--publish` accepts: manifest, metrics, report,
    rankings and a copy of the judgements."""
    started = datetime.now(UTC)
    judge_info = judge_info or {}
    scores = {c: score(pq, qrels, queries, k, min_grade) for c, pq in results.items()}
    lenient = {c: score(pq, qrels, queries, k, 1) for c, pq in results.items()}
    reference = reference or (REFERENCE_MODE if REFERENCE_MODE in results else next(iter(results)))
    company_types = [t for t in QUERY_TYPES if t != "generic"]
    comparisons = compare_configs(scores, reference)
    comparisons_company = compare_configs(scores, reference, types=company_types)
    sha, dirty = _git()
    run_dir = new_run_dir(out_root or RUNS_DIR, f"{started:%Y%m%dT%H%M%SZ}-retrieval-pooled")
    run_id = run_dir.name
    judged_docs = sum(len(d) for d in qrels.values())
    retrievers = retrievers or {}
    first_store = next((d for d in retrievers.values() if d.get("store")), {})
    manifest = {
        "run_id": run_id, "system": "+".join(sorted({parse_mode(c, "baseline-rag")[0] for c in results})),
        "task": "retrieval", "conditions": [], "dataset_id": "retrieval-queries",
        "dataset_hash": hashlib.sha256(Path(queries_path).read_bytes()).hexdigest()[:12],
        "label_source": judge_info.get("judge", "qrels"), "n_items": len(queries),
        "git_sha": sha, "git_dirty": dirty,
        "llm": {"judge_model": judge_info.get("model")}, "repeats": 1, "seed": SEED,
        "started_at": started.isoformat(), "finished_at": datetime.now(UTC).isoformat(),
        "config": {
            "split": "dev", "k": k, "min_grade": min_grade, "reference": reference,
            "queries": Path(queries_path).as_posix(), "qrels": Path(qrels_path).as_posix(),
            "query_counts": {t: sum(q.get("type") == t for q in queries) for t in QUERY_TYPES},
            "pool": {"documents": judged_docs,
                     "relevant": sum(g >= min_grade for d in qrels.values() for g in d.values()),
                     "relevant_lenient": sum(g >= 1 for d in qrels.values() for g in d.values())},
            "classifier": {"style": "judge-relevance"}, "retriever": first_store, "retrievers": retrievers,
            "judge": judge_info,
        },
    }
    metrics = {
        "run_id": run_id, "task": "retrieval", "k": k, "min_grade": min_grade, "reference": reference,
        "conditions": {},   # the results index reads this key; a retrieval run has no classifier arm
        "configs": {c: {k_: v for k_, v in b.items() if k_ != "per_query"} for c, b in scores.items()},
        "configs_lenient": {c: {k_: v for k_, v in b.items() if k_ != "per_query"}
                            for c, b in lenient.items()},
        "against_reference": comparisons, "against_reference_company_queries": comparisons_company,
        "per_query": {c: b["per_query"] for c, b in scores.items()},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    with (run_dir / "rankings.jsonl").open("w", encoding="utf-8") as f:
        for config, per_query in results.items():
            for query_id, spans in per_query.items():
                f.write(json.dumps({"config": config, "query_id": query_id,
                                    "ranked": [s.statement_id for s in spans]}) + "\n")
    (run_dir / "qrels.jsonl").write_bytes(Path(qrels_path).read_bytes())
    (run_dir / "report.md").write_text(report_md(run_id, manifest, scores, lenient, comparisons, judge_info),
                                       encoding="utf-8")
    return run_dir
