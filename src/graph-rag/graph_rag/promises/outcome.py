"""What became of each checkable promise: evidence from the deadline-year reports, and a proposed outcome.

Evidence is looked for where the outcome should be reported: the company's reports for the deadline
year and the year after. Retrieval is hybrid over *all* parsed statements of those reports, tables
included (performance tables are where "target met" usually lives): BM25 over every statement, dense
over the prose sentences that have vectors in the shared sentence store, fused with RRF.

The outcome is a proposal only: RQ2's numbers come from the human-checked sheet (`sheet.py`), and this
module's labels are what that sheet scores. Two judges:

- `v1` asks the LLM for the outcome directly (`configs/prompts/promise_outcome.md`). On the human check
  it over-committed: it gave a verdict on 21 of the 35 promises the annotator called unclear.
- `v2` (default) asks the LLM only to label each evidence statement (is it about this very target, does
  it state the deadline year's result, does it move the commitment) and derives the outcome from those
  labels with a fixed rule, `decide`, that falls back to `unclear`. `configs/prompts/promise_outcome_v2.md`.
"""

from __future__ import annotations

import json
import os
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

PROMPTS = {"v1": REPO_ROOT / "configs" / "prompts" / "promise_outcome.md",
           "v2": REPO_ROOT / "configs" / "prompts" / "promise_outcome_v2.md"}
PROMPT_PATH = PROMPTS["v1"]
OUTCOMES = ("achieved", "failed", "revised", "unclear", "disappeared")
RELATIONS = ("this_target", "same_metric", "other")
RESULTS = ("met", "missed", "none")
CHANGES = ("later", "none")
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


def _ask(promise: dict, evidence: list[dict], client: LLMClient, prompt: dict[str, str],
         max_tokens: int) -> dict:
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
                        max_tokens=max_tokens, response_format={"type": "json_object"})
    match = _JSON.search(reply.text or "")
    try:
        obj = json.loads(match.group(0)) if match else {}
    except ValueError:
        obj = {}
    return obj if isinstance(obj, dict) else {}


_NOTHING = {"outcome": "disappeared", "rationale": "No statements were retrieved for the deadline years.",
            "evidence_refs": [], "parse_ok": True}


def propose(promise: dict, evidence: list[dict], client: LLMClient, prompt: dict[str, str]) -> dict:
    """Judge v1: the model names the outcome."""
    if not evidence:
        return dict(_NOTHING)
    obj = _ask(promise, evidence, client, prompt, max_tokens=600)
    outcome = str(obj.get("outcome", "")).strip().lower()
    refs = [str(r).strip("[] ").upper() for r in obj.get("evidence", []) if isinstance(r, str)]
    valid = {e["ref"] for e in evidence}
    return {"outcome": outcome if outcome in OUTCOMES else "unclear",
            "rationale": str(obj.get("rationale") or "").strip(),
            "evidence_refs": [r for r in refs if r in valid],
            "parse_ok": outcome in OUTCOMES}


def parse_labels(obj: dict, evidence: list[dict]) -> tuple[list[dict], bool]:
    """One label per evidence statement, in evidence order, and whether the reply covered them all.

    A result or a change is kept only on a statement the model placed on this very target, so a sloppy
    reply cannot produce a verdict from a statement about something else.
    """
    given = {}
    for item in obj.get("evidence") or []:
        if isinstance(item, dict):
            given[str(item.get("ref", "")).strip("[] ").upper()] = item
    labels, complete = [], isinstance(obj.get("annual"), bool)
    for e in evidence:
        raw = given.get(e["ref"], {})
        relation = str(raw.get("relation", "")).strip().lower()
        if relation not in RELATIONS:
            relation, complete = "other", False
        mine = relation == "this_target"
        result = str(raw.get("deadline_result", "")).strip().lower()
        change = str(raw.get("change", "")).strip().lower()
        labels.append({"ref": e["ref"], "relation": relation,
                       "deadline_result": result if mine and result in RESULTS else "none",
                       "change": change if mine and change in CHANGES else "none"})
    return labels, complete


def decide(labels: list[dict], annual: bool) -> tuple[str, list[str]]:
    """The outcome the evidence labels support, and the statements it rests on.

    A verdict needs a statement about this very target that states it: the deadline year's result for
    achieved and failed, a later or dropped deadline for revised. A reported result beats a restatement
    (the guide: revised only "without reporting the original as met"), and a moved goalpost beats a miss,
    which it explains. An annual target set again for a later year is routine renewal and settles
    nothing. Contradictory results, statements about the metric that are not about this commitment, and
    renewals leave it unclear; disappeared means no statement concerns the metric at all.

    Not detected, by design: an annual target renewed at a weaker level. Telling that from a company's
    other targets on the same metric needs more than one statement at a time.
    """
    mine = [x for x in labels if x["relation"] == "this_target"]
    met = [x["ref"] for x in mine if x["deadline_result"] == "met"]
    missed = [x["ref"] for x in mine if x["deadline_result"] == "missed"]
    later = [x["ref"] for x in mine if x["change"] == "later"]
    if met and not missed:
        return "achieved", met
    if later and not met and not annual:
        return "revised", later
    if missed and not met:
        return "failed", missed
    touched = [x["ref"] for x in labels if x["relation"] != "other"]
    return ("unclear", touched) if touched else ("disappeared", [])


def propose_v2(promise: dict, evidence: list[dict], client: LLMClient, prompt: dict[str, str]) -> dict:
    """Judge v2: the model labels the evidence, `decide` names the outcome."""
    if not evidence:
        return {**_NOTHING, "labels": [], "annual": bool(promise["recurring"]), "model_outcome": None}
    obj, labels, complete = {}, [], False
    for max_tokens in (1500, 3000):                # an empty or cut-off reply gets one longer retry
        obj = _ask(promise, evidence, client, prompt, max_tokens=max_tokens)
        labels, complete = parse_labels(obj, evidence)
        if complete:
            break
    # the extraction's own flag counts too: either reading of "annual" makes a later year a renewal
    annual = bool(promise["recurring"]) or obj.get("annual") is True
    outcome, refs = decide(labels, annual) if complete else ("unclear", [])  # a garbled reply settles nothing
    stated = str(obj.get("outcome", "")).strip().lower()
    return {"outcome": outcome, "rationale": str(obj.get("rationale") or "").strip(),
            "evidence_refs": refs, "parse_ok": complete, "labels": labels, "annual": annual,
            "model_outcome": stated if stated in OUTCOMES else None}


JUDGES = {"v1": propose, "v2": propose_v2}


def vote(outcomes: list[str]) -> str:
    """Strict majority over repeats, otherwise unclear: a verdict the judge does not reproduce is not one."""
    top, count = Counter(outcomes).most_common(1)[0]
    return top if count * 2 > len(outcomes) else "unclear"


def outcomes_path(cfg: GraphConfig, judge: str) -> Path:
    return out_dir(cfg) / ("outcomes.jsonl" if judge == "v1" else f"outcomes.{judge}.jsonl")


def run(cfg: GraphConfig, limit: int | None = None, workers: int = 8, client: LLMClient | None = None,
        judge: str = "v2", evidence_from: Path | None = None, repeats: int = 1) -> dict:
    """Judge every checkable promise.

    `evidence_from` reuses the evidence stored in an earlier outcomes file, so two judges are compared on
    identical statements (and a filled human sheet, judged "from the evidence shown", stays valid).
    `repeats` > 1 bypasses the response cache and takes the majority outcome.
    """
    if repeats > 1 and client is None:
        os.environ["GW_LLM_CACHE"] = "0"
    client = client or LLMClient()
    prompt = _sections(PROMPTS[judge])
    propose_fn = JUDGES[judge]
    base = out_dir(cfg)
    lines = (base / "promises.jsonl").read_text(encoding="utf-8").splitlines()
    promises = [json.loads(line) for line in lines if line]
    todo = [p for p in promises if p["checkable"]]
    if limit:
        todo = todo[:limit]
    evidence: dict[str, list[dict]] = {}
    if evidence_from:
        for line in Path(evidence_from).read_text(encoding="utf-8").splitlines():
            if line:
                row = json.loads(line)
                evidence[row["promise_id"]] = row["evidence"]
    reused = sum(p["promise_id"] in evidence for p in todo)
    finder = EvidenceFinder(cfg, client) if reused < len(todo) else None
    for p in todo:                                                 # DuckDB is not thread-safe: do it serially
        if p["promise_id"] not in evidence:
            evidence[p["promise_id"]] = finder.find(p)

    def one(p: dict) -> dict:
        runs = [propose_fn(p, evidence[p["promise_id"]], client, prompt) for _ in range(max(1, repeats))]
        votes = [r["outcome"] for r in runs]
        final = vote(votes)
        kept = next((r for r in runs if r["outcome"] == final), runs[0])
        result = {"promise_id": p["promise_id"], **kept, "outcome": final,
                  "parse_ok": all(r["parse_ok"] for r in runs), "evidence": evidence[p["promise_id"]]}
        if repeats > 1:
            result["votes"] = votes
            if kept["outcome"] != final:                           # no majority: nothing to rest on
                result["evidence_refs"] = []
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, todo))
    out = outcomes_path(cfg, judge)
    with out.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats = {
        "judge": judge,
        "prompt": PROMPTS[judge].name,
        "promises_judged": len(results),
        "proposed_outcome": dict(Counter(r["outcome"] for r in results)),
        "unparsed": sum(not r["parse_ok"] for r in results),
        "mean_evidence": sum(len(r["evidence"]) for r in results) / max(1, len(results)),
        "evidence_reused": reused,
        "dense_used": finder.vectors is not None if finder else None,
        "repeats": repeats,
        "unstable": sum(len(set(r["votes"])) > 1 for r in results) if repeats > 1 else None,
        "llm": {"model": client.settings.chat_model, "effort": client.settings.reasoning_effort,
                "calls": client.usage["calls"], "input_tokens": client.usage["input_tokens"],
                "output_tokens": client.usage["output_tokens"],
                "cost_usd": client.settings.cost_usd(client.usage["input_tokens"],
                                                     client.usage["output_tokens"])},
        "out": str(out),
    }
    if judge != "v1":
        stats["model_outcome"] = dict(Counter(str(r.get("model_outcome")) for r in results))
    stats_name = "outcomes_stats.json" if judge == "v1" else f"outcomes_stats.{judge}.json"
    (base / stats_name).write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
