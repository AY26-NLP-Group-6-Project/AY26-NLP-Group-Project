"""Model-made relevance judgements for the pooled retrieval evaluation (`retrieval.py`).

The pool is the union of every configuration's top-k for every query. The brief meant a person to grade
it; none was available, so the group's chat model does, with the discipline of the RAG-metric judge: a
fixed prompt under version control, every grade and its reason stored, the blind sheet (`pool.csv`) kept
so a person can grade a sample later and the agreement be reported. The judge is a model, and it may be
the model whose embeddings the dense index uses; wherever its numbers are quoted, say they are model
judgements.

    gw-eval --task retrieval --judge-pool pool.csv --queries queries.jsonl --qrels qrels.jsonl

Grades are 0-3 (`GRADES`); `retrieval.score` counts a document relevant from `min_grade` up.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gw_common.llm import REPO_ROOT, LLMClient

PROMPT_PATH = REPO_ROOT / "configs" / "prompts" / "relevance_judge.md"
DOCS_PER_CALL = 10
DOC_CHARS = 600
GRADES = {0: "not relevant", 1: "marginal", 2: "relevant", 3: "highly relevant"}
UNJUDGED = "unjudged: no verdict in the reply"
_JSON_RE = re.compile(r"\{.*\}", re.S)


def _sections(path: Path = PROMPT_PATH) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## (system|user)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def _json(text: str) -> dict | None:
    match = _JSON_RE.search(text or "")
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def load_pool(path: Path) -> list[dict]:
    """The judging sheet `retrieval.export_pool` wrote: one row per pooled (query, document)."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def describe_query(q: dict) -> str:
    """The query as the judge sees it: its type, text, filters and the years the results may come from."""
    lines = [f"type: {q.get('type', 'generic')}", f"text: {q['text']}"]
    if q.get("company"):
        lines.append(f"company: {q['company']}")
    if q.get("aspect") and q.get("aspect") != q.get("text"):
        lines.append(f"aspect: {q['aspect']}")
    if q.get("anchor_year"):
        lines.append(f"years: the company's report years other than {q['anchor_year']}, the year of the query"
                     " sentence")
    elif q.get("year_from") or q.get("year_to"):
        lines.append(f"years: {q.get('year_from') or '…'} to {q.get('year_to') or '…'}")
    elif q.get("company"):
        lines.append("years: any report year of the company")
    else:
        lines.append("scope: every company and year")
    return "\n".join(lines)


def describe_docs(rows: Sequence[dict]) -> str:
    return "\n".join(
        f"[D{i}] ({r.get('doc_company', '')}, {r.get('doc_year', '')}, p.{r.get('doc_page', '')}) "
        f"{(r.get('text') or '')[:DOC_CHARS]}"
        for i, r in enumerate(rows, 1)
    )


class RelevanceJudge:
    def __init__(self, client: LLMClient | None = None, workers: int = 8) -> None:
        self.client = client or LLMClient()
        self.workers = workers
        self._prompt = _sections()

    def describe(self) -> dict[str, object]:
        """What the qrels file records about how it was made."""
        settings = getattr(self.client, "settings", None)
        return {"judge": "llm", "model": getattr(settings, "chat_model", None), "prompt": PROMPT_PATH.name,
                "prompt_sha256": hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()[:12],
                "docs_per_call": DOCS_PER_CALL, "doc_chars": DOC_CHARS, "grades": GRADES}

    def _ask(self, query: dict, rows: Sequence[dict]) -> dict[str, tuple[int, str]]:
        messages = [
            {"role": "system", "content": self._prompt["system"]},
            {"role": "user", "content": self._prompt["user"].format(
                query_block=describe_query(query), docs_block=describe_docs(rows))},
        ]
        obj = _json(self.client.chat(messages, max_tokens=900).text)
        if obj is None:  # one more try with the gateway holding the model to JSON
            obj = _json(self.client.chat(messages, max_tokens=900,
                                         response_format={"type": "json_object"}).text)
        out: dict[str, tuple[int, str]] = {}
        for entry in (obj or {}).get("grades") or []:
            if not isinstance(entry, dict):
                continue
            ref = str(entry.get("ref", "")).strip().upper().strip("[]")
            if not re.fullmatch(r"D\d+", ref) or not 1 <= int(ref[1:]) <= len(rows):
                continue
            try:
                grade = max(0, min(3, int(entry.get("grade"))))
            except (TypeError, ValueError):
                continue
            out[rows[int(ref[1:]) - 1]["doc_id"]] = (grade, str(entry.get("reason") or "")[:160])
        return out

    def judge(self, pool: Sequence[dict], queries: Sequence[dict]) -> tuple[dict[str, dict[str, dict]], dict]:
        """Grade every pooled document; returns query_id -> doc_id -> {grade, reason}, and a summary.

        One call grades up to `DOCS_PER_CALL` documents of one query, so grades within a query are made
        side by side. A document the reply did not grade is recorded as 0 with `UNJUDGED`, and counted.
        """
        by_query = {q["query_id"]: q for q in queries}
        rows_of: dict[str, list[dict]] = {}
        for row in pool:
            if row["query_id"] in by_query:
                rows_of.setdefault(row["query_id"], []).append(row)
        tasks = [(by_query[qid], rows[i:i + DOCS_PER_CALL])
                 for qid, rows in rows_of.items() for i in range(0, len(rows), DOCS_PER_CALL)]
        with ThreadPoolExecutor(max_workers=self.workers) as pool_:
            answers = list(pool_.map(lambda t: self._ask(*t), tasks))

        out: dict[str, dict[str, dict]] = {qid: {} for qid in rows_of}
        unjudged = 0
        for (query, rows), graded in zip(tasks, answers, strict=True):
            for row in rows:
                grade, reason = graded.get(row["doc_id"], (0, UNJUDGED))
                unjudged += reason == UNJUDGED
                out[query["query_id"]][row["doc_id"]] = {"grade": grade, "reason": reason}
        counts = {g: 0 for g in GRADES}
        for docs in out.values():
            for d in docs.values():
                counts[d["grade"]] += 1
        usage = dict(getattr(self.client, "usage", {}) or {})
        settings = getattr(self.client, "settings", None)
        cost = (settings.cost_usd(usage.get("input_tokens", 0), usage.get("output_tokens", 0))
                if settings is not None and hasattr(settings, "cost_usd") else None)
        summary = {"queries": len(out), "documents": sum(len(d) for d in out.values()), "calls": len(tasks),
                   "unjudged": unjudged, "grade_counts": {GRADES[g]: n for g, n in counts.items()},
                   "usage": usage, "cost_usd": cost}
        return out, summary


def write_qrels(qrels: dict[str, dict[str, dict]], path: Path, judge_info: dict) -> Path:
    """One line per query, in the format `retrieval.load_qrels` reads, with the reasons and the judge kept."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for qid in sorted(qrels):
            docs = qrels[qid]
            f.write(json.dumps({
                "query_id": qid,
                "relevant": {doc: d["grade"] for doc, d in docs.items()},
                "reasons": {doc: d["reason"] for doc, d in docs.items()},
                "judge": judge_info,
            }, ensure_ascii=False) + "\n")
    return path


def load_qrels_meta(path: Path) -> dict:
    """The `judge` record of a qrels file (empty for a hand-made file)."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            return json.loads(line).get("judge") or {}
    return {}
