"""What became of each checkable promise: evidence from the deadline-year reports, and a proposed outcome.

Evidence is looked for where the outcome should be reported: the company's reports for the deadline
year and the year after. Retrieval is hybrid over *all* parsed statements of those reports, tables
included (performance tables are where "target met" usually lives): BM25 over every statement, dense
over the prose sentences that have vectors in the shared sentence store, fused with RRF.

The outcome is proposed by the LLM under `configs/prompts/promise_outcome.md` and is a proposal only:
RQ2's numbers come from the human-checked sheet (`sheet.py`), and this module's labels are what that
sheet scores.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
from baseline_rag import chunks as chunk_store
from baseline_rag.index import BM25, rrf
from gw_common.evidence import normalise
from gw_common.llm import REPO_ROOT, LLMClient

from graph_rag.config import GraphConfig
from graph_rag.promises.extract import out_dir
from graph_rag.store.duckdb_store import DuckDBGraphStore

PROMPT_PATH = REPO_ROOT / "configs" / "prompts" / "promise_outcome.md"
OUTCOMES = ("achieved", "failed", "revised", "unclear", "disappeared")
EVIDENCE_K = 6
EVIDENCE_CHARS = 500
CANDIDATES = 40
MIN_WORDS = 5
SENTENCE_STORE = "dev-sent"
_JSON = re.compile(r"\{.*\}", re.S)


def _sections(path: Path = PROMPT_PATH) -> dict[str, str]:
    parts = re.split(r"^## (system|user)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


class EvidenceFinder:
    def __init__(self, cfg: GraphConfig, client: LLMClient, sentence_store: str = SENTENCE_STORE) -> None:
        self.store = DuckDBGraphStore(cfg.db_path, read_only=True)
        self.client = client
        try:
            chunks, self.vectors, _ = chunk_store.load(sentence_store)
            self.row_of = {c.chunk_id: i for i, c in enumerate(chunks)}
        except FileNotFoundError:        # dense is an improvement, not a requirement
            self.vectors, self.row_of = None, {}

    @lru_cache(maxsize=256)  # noqa: B019 - one finder per run
    def _index(self, company: str, years: tuple[int, ...]):
        placeholders = ",".join("?" * len(years))
        rows = self.store.con.execute(
            f"SELECT stmt_id, year, page, sha256, text FROM statements "
            f"WHERE company = ? AND year IN ({placeholders}) ORDER BY year, page, idx",
            [company, *years],
        ).fetchall()
        docs, seen = [], set()
        for stmt_id, year, page, sha, text in rows:
            key = (year, normalise(text))
            if len(text.split()) < MIN_WORDS or key in seen:
                continue
            seen.add(key)
            docs.append({"stmt_id": stmt_id, "year": year, "page": page, "file": sha, "text": text})
        return docs, BM25([d["text"] for d in docs])

    def find(self, promise: dict, k: int = EVIDENCE_K) -> list[dict]:
        years = tuple(promise["outcome_years"])
        if not years:
            return []
        docs, bm25 = self._index(promise["company"], years)
        if not docs:
            return []
        query = f"{promise['metric']}. {promise['origin']['target_text']}"
        sparse = bm25.search(query, None, CANDIDATES)
        rankings = [sparse]
        if self.vectors is not None:
            rows = [(i, self.row_of[d["stmt_id"]]) for i, d in enumerate(docs) if d["stmt_id"] in self.row_of]
            if rows:
                qv = np.asarray(self.client.embed([query])[0], dtype=np.float32)
                scores = self.vectors[[r for _, r in rows]] @ qv
                order = np.argsort(-scores)[:CANDIDATES]
                rankings.append([(rows[j][0], float(scores[j])) for j in order])
        fused = rrf(*rankings)[:k]
        return [{"ref": f"E{n}", **docs[i]} for n, (i, _) in enumerate(fused, 1)]


def _target_phrase(p: dict) -> tuple[str, str]:
    quantity = ""
    if p["quantity"] is not None:
        number = int(p["quantity"]) if float(p["quantity"]).is_integer() else p["quantity"]
        quantity = f" — {p['direction'] or 'target'} {number}{p['unit'] or ''}"
    baseline = f" (baseline {p['baseline_year']})" if p["baseline_year"] else ""
    return quantity, baseline


def propose(promise: dict, evidence: list[dict], client: LLMClient, prompt: dict[str, str]) -> dict:
    if not evidence:
        return {"outcome": "disappeared", "rationale": "No statements were retrieved for the deadline years.",
                "evidence_refs": [], "parse_ok": True}
    quantity, baseline = _target_phrase(promise)
    block = "\n".join(f"[{e['ref']}] ({e['year']} report, p.{e['page']}) {e['text'][:EVIDENCE_CHARS]}"
                      for e in evidence)
    user = prompt["user"].format(
        company=promise["company"], origin_year=promise["origin"]["year"],
        origin_page=promise["origin"]["page"], origin_text=promise["origin"]["text"][:700],
        metric=promise["metric"], quantity=quantity, baseline=baseline,
        target_year=promise["target_year"], evidence=block,
        recurring=" (RECURRING annual target)" if promise["recurring"] else "",
    )
    reply = client.chat([{"role": "system", "content": prompt["system"]}, {"role": "user", "content": user}],
                        max_tokens=600, response_format={"type": "json_object"})
    match = _JSON.search(reply.text or "")
    try:
        obj = json.loads(match.group(0)) if match else {}
    except ValueError:
        obj = {}
    outcome = str(obj.get("outcome", "")).strip().lower()
    refs = [str(r).strip("[] ").upper() for r in obj.get("evidence", []) if isinstance(r, str)]
    valid = {e["ref"] for e in evidence}
    return {"outcome": outcome if outcome in OUTCOMES else "unclear",
            "rationale": str(obj.get("rationale") or "").strip(),
            "evidence_refs": [r for r in refs if r in valid],
            "parse_ok": outcome in OUTCOMES}


def run(cfg: GraphConfig, limit: int | None = None, workers: int = 8,
        client: LLMClient | None = None) -> dict:
    client = client or LLMClient()
    prompt = _sections()
    base = out_dir(cfg)
    lines = (base / "promises.jsonl").read_text(encoding="utf-8").splitlines()
    promises = [json.loads(line) for line in lines if line]
    todo = [p for p in promises if p["checkable"]]
    if limit:
        todo = todo[:limit]
    finder = EvidenceFinder(cfg, client)
    evidence = {p["promise_id"]: finder.find(p) for p in todo}     # DuckDB is not thread-safe: do it serially

    def one(p: dict) -> dict:
        return {"promise_id": p["promise_id"], **propose(p, evidence[p["promise_id"]], client, prompt),
                "evidence": evidence[p["promise_id"]]}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, todo))
    with (base / "outcomes.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats = {
        "promises_judged": len(results),
        "proposed_outcome": dict(Counter(r["outcome"] for r in results)),
        "unparsed": sum(not r["parse_ok"] for r in results),
        "mean_evidence": sum(len(r["evidence"]) for r in results) / max(1, len(results)),
        "dense_used": finder.vectors is not None,
        "llm": {"model": client.settings.chat_model, "effort": client.settings.reasoning_effort,
                "calls": client.usage["calls"]},
        "out": str(base / "outcomes.jsonl"),
    }
    (base / "outcomes_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
