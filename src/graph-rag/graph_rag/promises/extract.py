"""Structured targets: the dated commitments RQ2 follows across years.

Two steps, both auditable:

1. **Candidates** by rule: a statement that mentions a year not before its report year and a
   commitment cue. Recall-oriented and cheap; it only decides what the LLM gets to read.
2. **Extraction** by LLM into a fixed schema (`configs/prompts/target_extraction.md`), then validated
   mechanically: the quoted span must occur in the statement, the deadline must be a plausible year not
   before the report year, the category must be one of A3CG's. Anything that fails is dropped and
   counted, never repaired silently.

Output: `artifacts/graph/<build>/promises/targets.jsonl`, one line per extracted target.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gw_common.evidence import normalise
from gw_common.llm import REPO_ROOT, LLMClient

from graph_rag.config import GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore

PROMPT_PATH = REPO_ROOT / "configs" / "prompts" / "target_extraction.md"
CATEGORIES = {
    "resource optimisation", "waste management", "emissions control", "ecological conservation",
    "workplace", "outreach", "management", "business compliance",
    "worker & consumer safety compliance", "data and cybersecurity protection",
}
KINDS = {"quantitative", "milestone", "qualitative"}
DIRECTIONS = {"reduce", "increase", "maintain", "achieve"}
MIN_WORDS, MAX_WORDS = 6, 80
YEAR_MAX = 2060
_YEAR = re.compile(r"\b(?:FY\s?)?(20[2-5]\d)\b|\bFY\s?(2[0-9])\b", re.I)
_CUE = re.compile(
    r"\b(target\w*|aim\w*|goal\w*|commit\w*|pledg\w*|plan(?:s|ned)? to|striv\w*|ambition\w*|net[- ]zero|"
    r"carbon[- ]neutral\w*|by (?:FY\s?)?20[2-5]\d|will (?:reduce|achieve|increase|maintain|complete|"
    r"implement|install|transition|phase)|intend\w* to|seek\w* to|roadmap)\b", re.I)
_JSON = re.compile(r"\{.*\}", re.S)
# An outside extractor may resolve an anaphoric metric from the neighbouring sentence and say so in the
# field. The resolution is kept, the remark is stripped, and the target is flagged.
_FROM_CONTEXT = re.compile(r",?\s*per the preceding sentences? of the report", re.I)


def out_dir(cfg: GraphConfig) -> Path:
    path = cfg.out_dir / "promises"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_candidate(text: str, report_year: int) -> bool:
    if not MIN_WORDS <= len(text.split()) <= MAX_WORDS or not _CUE.search(text):
        return False
    years = [int(a or "20" + b) for a, b in _YEAR.findall(text)]
    return any(y >= report_year for y in years)


def candidates(store: DuckDBGraphStore) -> list[dict]:
    rows = store.con.execute(
        "SELECT stmt_id, company, year, page, sha256, text FROM statements ORDER BY company, year, page, idx"
    ).fetchall()
    return [{"stmt_id": s, "company": c, "year": y, "page": p, "file": f, "text": t}
            for s, c, y, p, f, t in rows if t and is_candidate(t, y)]


def _sections(path: Path = PROMPT_PATH) -> dict[str, str]:
    parts = re.split(r"^## (system|user)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def validate(raw: dict, statement: str, report_year: int) -> tuple[dict | None, str]:
    """A cleaned target, or (None, reason). Nothing is inferred: a field that fails is a rejection."""
    if not isinstance(raw, dict):
        return None, "not_an_object"
    span = str(raw.get("target_text") or "").strip()
    if not span or normalise(span) not in normalise(statement):
        return None, "span_not_in_statement"
    try:
        target_year = int(raw.get("target_year"))
    except (TypeError, ValueError):
        return None, "no_target_year"
    if not report_year <= target_year <= YEAR_MAX:
        return None, "target_year_out_of_range"
    metric = str(raw.get("metric") or "").strip()
    if not metric:
        return None, "no_metric"
    category = str(raw.get("category") or "").strip().lower()
    kind = str(raw.get("kind") or "").strip().lower()
    direction = str(raw.get("direction") or "").strip().lower()
    quantity = raw.get("quantity")
    baseline = raw.get("baseline_year")
    try:
        baseline = int(baseline) if baseline is not None else None
    except (TypeError, ValueError):
        baseline = None
    return {
        "target_text": span,
        "metric": metric,
        "category": category if category in CATEGORIES else None,
        "direction": direction if direction in DIRECTIONS else None,
        "quantity": float(quantity) if isinstance(quantity, (int, float)) else None,
        "unit": (str(raw["unit"]).strip() or None) if raw.get("unit") is not None else None,
        "baseline_year": baseline,
        "target_year": target_year,
        "kind": kind if kind in KINDS else "qualitative",
        "recurring": bool(raw.get("recurring")),
    }, "ok"


def extract(cfg: GraphConfig, limit: int | None = None, workers: int = 8,
            client: LLMClient | None = None) -> dict:
    client = client or LLMClient()
    prompt = _sections()
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        cands = candidates(store)
    if limit:
        cands = cands[:limit]

    def one(c: dict) -> tuple[dict, list[dict], Counter]:
        user = prompt["user"].format(company=c["company"], year=c["year"], text=c["text"])
        messages = [{"role": "system", "content": prompt["system"]}, {"role": "user", "content": user}]
        reply = client.chat(messages, max_tokens=1600, response_format={"type": "json_object"})
        match = _JSON.search(reply.text or "")
        reasons: Counter = Counter()
        try:
            raw_targets = json.loads(match.group(0)).get("targets", []) if match else None
        except ValueError:
            raw_targets = None
        if raw_targets is None:
            reasons["unparseable_reply"] += 1
            return c, [], reasons
        kept = []
        for raw in raw_targets if isinstance(raw_targets, list) else []:
            target, reason = validate(raw, c["text"], c["year"])
            reasons[reason] += 1
            if target:
                kept.append(target)
        return c, kept, reasons

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, cands))

    path = out_dir(cfg) / "targets.jsonl"
    reasons_total: Counter = Counter()
    n_targets = 0
    with path.open("w", encoding="utf-8") as f:
        for c, targets, reasons in results:
            reasons_total.update(reasons)
            for i, t in enumerate(targets):
                n_targets += 1
                f.write(json.dumps({"target_id": f"{c['stmt_id']}#{i}", **c, **t}, ensure_ascii=False) + "\n")
    with_target = sum(bool(t) for _, t, _ in results)
    kept = [t for _, ts, _ in results for t in ts]
    stats = {
        "candidates": len(cands),
        "statements_with_target": with_target,
        "targets": n_targets,
        "companies": len({c["company"] for c, ts, _ in results if ts}),
        "validation": dict(reasons_total),
        "by_kind": dict(Counter(t["kind"] for t in kept)),
        "recurring": sum(t["recurring"] for t in kept),
        "with_quantity": sum(t["quantity"] is not None for t in kept),
        "with_baseline_year": sum(t["baseline_year"] is not None for t in kept),
        "target_year": dict(sorted(Counter(t["target_year"] for t in kept).items())),
        "llm": {"model": client.settings.chat_model, "effort": client.settings.reasoning_effort,
                "calls": client.usage["calls"], "input_tokens": client.usage["input_tokens"],
                "output_tokens": client.usage["output_tokens"]},
        "out": str(path),
    }
    (out_dir(cfg) / "targets_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


# ----------------------------------------------------------------------------- hand-off to another extractor
def export_shards(cfg: GraphConfig, shards: int = 12) -> dict:
    """Write the candidate statements as shard files for an extractor outside this pipeline.

    Same candidates the in-repo extractor reads, so the two can be compared statement by statement.
    Each line: {stmt_id, company, year, text}. The extractor returns, for every line, one JSON line
    {stmt_id, targets: [...]} following `configs/prompts/target_extraction.md`.
    """
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        cands = candidates(store)
    base = out_dir(cfg) / "handoff"
    base.mkdir(parents=True, exist_ok=True)
    size = -(-len(cands) // shards)
    files = []
    for k in range(shards):
        part = cands[k * size:(k + 1) * size]
        if not part:
            break
        path = base / f"shard_{k + 1:02d}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for c in part:
                f.write(json.dumps({"stmt_id": c["stmt_id"], "company": c["company"], "year": c["year"],
                                    "text": c["text"]}, ensure_ascii=False) + "\n")
        files.append({"shard": path.name, "statements": len(part)})
    return {"candidates": len(cands), "shards": files, "dir": str(base)}


def ingest(cfg: GraphConfig, source: str, pattern: str = "out_*.jsonl") -> dict:
    """Validate an outside extractor's output with the same rules and write `targets.<source>.jsonl`."""
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        by_id = {c["stmt_id"]: c for c in candidates(store)}
    base = out_dir(cfg)
    reasons: Counter = Counter()
    seen: set[str] = set()
    kept: list[dict] = []
    for path in sorted((base / "handoff").glob(pattern)):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                reasons["unparseable_line"] += 1
                continue
            c = by_id.get(str(record.get("stmt_id")))
            if c is None:
                reasons["unknown_stmt_id"] += 1
                continue
            if c["stmt_id"] in seen:
                reasons["duplicate_stmt_id"] += 1
                continue
            seen.add(c["stmt_id"])
            targets = record.get("targets") or []
            for i, raw in enumerate(targets if isinstance(targets, list) else []):
                target, reason = validate(raw, c["text"], c["year"])
                reasons[reason] += 1
                if target:
                    from_context = bool(_FROM_CONTEXT.search(target["metric"]))
                    if from_context:
                        cleaned = _FROM_CONTEXT.sub("", target["metric"])
                        target["metric"] = re.sub(r"[()]", " ", cleaned).split()
                        target["metric"] = " ".join(target["metric"])
                    kept.append({"target_id": f"{c['stmt_id']}#{i}", **c, **target,
                                 "metric_from_context": from_context})
            del line_no
    out = base / f"targets.{source}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for t in kept:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    stats = {
        "source": source,
        "candidates": len(by_id),
        "statements_answered": len(seen),
        "statements_missing": len(by_id) - len(seen),
        "statements_with_target": len({t["stmt_id"] for t in kept}),
        "targets": len(kept),
        "companies": len({t["company"] for t in kept}),
        "validation": dict(reasons),
        "by_kind": dict(Counter(t["kind"] for t in kept)),
        "recurring": sum(t["recurring"] for t in kept),
        "with_quantity": sum(t["quantity"] is not None for t in kept),
        "target_year": dict(sorted(Counter(t["target_year"] for t in kept).items())),
        "out": str(out),
    }
    (base / f"targets_stats.{source}.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
