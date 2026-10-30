"""What became of each checkable promise: the shared judge (`gw_common.judges.promise`) run over the
evidence `evidence.py` finds, once per promise, with repeats and a majority vote.

The outcome is a proposal only: RQ2's numbers come from the gold set and the human-checked sheets
(`gold.py`, `sheet.py`), and this module's labels are what those score. The judge itself lives in
`gw_common` because every retrieval arm is read by the same one; its names are re-exported here for the
pipeline's stages and the tests.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gw_common.judges.promise import (
    CHANGES,
    EVIDENCE_CHARS,
    JUDGES,
    OUTCOMES,
    PROMPTS,
    RELATIONS,
    REPORTED,
    RESULTS,
    decide,
    parse_labels,
    propose,
    propose_v2,
    reported,
    sections,
    vote,
)
from gw_common.llm import LLMClient

from graph_rag.config import GraphConfig
from graph_rag.promises import evidence as evidence_store
from graph_rag.promises.extract import out_dir

PROMPT_PATH = PROMPTS["v1"]
_sections = sections

__all__ = ["CHANGES", "EVIDENCE_CHARS", "JUDGES", "OUTCOMES", "PROMPTS", "RELATIONS", "REPORTED", "RESULTS",
           "decide", "outcomes_path", "parse_labels", "propose", "propose_v2", "reported", "run", "vote"]


def _suffix(judge: str, evidence: str) -> str:
    """outcomes.jsonl is v1 on deadline evidence, the first run; every other combination says what it is."""
    return ("" if judge == "v1" else f".{judge}") + ("" if evidence == "deadline" else f".{evidence}")


def outcomes_path(cfg: GraphConfig, judge: str, evidence: str = "deadline") -> Path:
    return out_dir(cfg) / f"outcomes{_suffix(judge, evidence)}.jsonl"


def run(cfg: GraphConfig, limit: int | None = None, workers: int = 8, client: LLMClient | None = None,
        judge: str = "v2", evidence: str = "trajectory", evidence_from: Path | None = None,
        repeats: int = 1) -> dict:
    """Judge every checkable promise on the evidence of mode `evidence`.

    The evidence is found once and kept (`evidence.<mode>.jsonl`), so judges and repeats run on identical
    statements. `evidence_from` takes it from another file instead, e.g. an earlier outcomes file, which
    keeps a filled human sheet, judged "from the evidence shown", valid; a system's evidence file
    (`evidence.<system>.jsonl`) names the output after the system. `repeats` > 1 bypasses the response
    cache and takes the majority outcome.
    """
    if evidence_from is None:
        evidence_from = evidence_store.evidence_path(cfg, evidence)
        if not evidence_from.exists():             # before the cache is switched off for the repeats
            evidence_store.build(cfg, evidence)
    elif Path(evidence_from).stem.startswith("evidence."):
        evidence = Path(evidence_from).stem[len("evidence."):]
    if repeats > 1 and client is None:
        os.environ["GW_LLM_CACHE"] = "0"
    client = client or LLMClient()
    prompt = sections(PROMPTS[judge])
    propose_fn = JUDGES[judge]
    base = out_dir(cfg)
    lines = (base / "promises.jsonl").read_text(encoding="utf-8").splitlines()
    promises = [json.loads(line) for line in lines if line]
    todo = [p for p in promises if p["checkable"]]
    if limit:
        todo = todo[:limit]
    found = evidence_store.load(Path(evidence_from))
    missing = [p["promise_id"] for p in todo if p["promise_id"] not in found]
    if missing:
        raise ValueError(f"{evidence_from} has no evidence for {len(missing)} promises, e.g. {missing[:3]}")
    evidence_of = {p["promise_id"]: found[p["promise_id"]] for p in todo}

    def one(p: dict) -> dict:
        shown = evidence_of[p["promise_id"]]
        runs = [propose_fn(p, shown, client, prompt) for _ in range(max(1, repeats))]
        votes = [r["outcome"] for r in runs]
        final = vote(votes)
        kept = next((r for r in runs if r["outcome"] == final), runs[0])
        result = {"promise_id": p["promise_id"], **kept, "outcome": final,
                  "parse_ok": all(r["parse_ok"] for r in runs), "evidence": shown}
        if repeats > 1:
            result["votes"] = votes
            if kept["outcome"] != final:                           # no majority: nothing to rest on
                result["evidence_refs"] = []
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, todo))
    out = outcomes_path(cfg, judge, evidence)
    with out.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats = {
        "judge": judge,
        "prompt": PROMPTS[judge].name,
        "evidence": evidence,
        "evidence_from": str(evidence_from),
        "promises_judged": len(results),
        "reported_outcome": dict(Counter(reported(r["outcome"]) for r in results)),
        "proposed_outcome": dict(Counter(r["outcome"] for r in results)),
        "unparsed": sum(not r["parse_ok"] for r in results),
        "mean_evidence": sum(len(r["evidence"]) for r in results) / max(1, len(results)),
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
    stats_name = f"outcomes_stats{_suffix(judge, evidence)}.json"
    (base / stats_name).write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
