"""What became of each checkable promise: a proposed outcome, judged from the evidence `evidence.py` finds.

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
from pathlib import Path

from gw_common.llm import REPO_ROOT, LLMClient

from graph_rag.config import GraphConfig
from graph_rag.promises import evidence as evidence_store
from graph_rag.promises.extract import out_dir

PROMPTS = {"v1": REPO_ROOT / "configs" / "prompts" / "promise_outcome.md",
           "v2": REPO_ROOT / "configs" / "prompts" / "promise_outcome_v2.md"}
PROMPT_PATH = PROMPTS["v1"]
OUTCOMES = ("achieved", "failed", "revised", "unclear", "disappeared")
REPORTED = ("achieved", "not_met", "unclear", "disappeared")
RELATIONS = ("this_target", "same_metric", "other")
RESULTS = ("met", "missed", "none")
CHANGES = ("later", "none")
EVIDENCE_CHARS = 500
_JSON = re.compile(r"\{.*\}", re.S)


def reported(outcome: str) -> str:
    """The outcome as it is reported: `failed` and `revised` are one class, not met.

    Both say the deadline passed without the target being reached. Which of the two it is depends on
    whether a missed target that is set again counts as re-dated, and neither the annotator across two
    rounds nor the judge drew that line the same way (`docs/promises.md`, section 7). The five-way label
    is kept as detail; counts, shares and agreement are reported on `REPORTED`.
    """
    return "not_met" if outcome in ("failed", "revised") else outcome


def _sections(path: Path = PROMPT_PATH) -> dict[str, str]:
    parts = re.split(r"^## (system|user)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


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
    block = "\n".join(f"[{e['ref']}] ({evidence_store.where(e)}) {e['text'][:EVIDENCE_CHARS]}"
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
        labels.append({"ref": e["ref"], "year": e.get("year"), "relation": relation,
                       "deadline_result": result if mine and result in RESULTS else "none",
                       "change": change if mine and change in CHANGES else "none"})
    return labels, complete


def decide(labels: list[dict], annual: bool, deadline: int | None = None) -> tuple[str, list[str]]:
    """The outcome the evidence labels support, and the statements it rests on.

    A verdict needs a statement about this very target that states it: the deadline year's result for
    achieved and failed, a later or dropped deadline for revised. A reported result beats a restatement
    (the guide: revised only "without reporting the original as met"), and a moved goalpost beats a miss,
    which it explains. An annual target set again for a later year is routine renewal and settles
    nothing. Contradictory results, statements about the metric that are not about this commitment, and
    renewals leave it unclear; disappeared means no statement concerns the metric at all.

    When the evidence spans the years before the deadline (`deadline` given, labels carry a report
    year), the calendar is enforced: a report older than the deadline year cannot state that a target was
    missed at the deadline, nor report an annual target's deadline-year result, though it can report a
    deliverable finished early; and a commitment repeated before its deadline and never mentioned from
    the deadline year on has disappeared.

    Not detected, by design: an annual target renewed at a weaker level. Telling that from a company's
    other targets on the same metric needs more than one statement at a time.
    """
    def due(x: dict) -> bool:                      # from a report of the deadline year or later
        return deadline is None or x.get("year") is None or x["year"] >= deadline

    mine = [x for x in labels if x["relation"] == "this_target"]
    met = [x["ref"] for x in mine if x["deadline_result"] == "met" and (due(x) or not annual)]
    missed = [x["ref"] for x in mine if x["deadline_result"] == "missed" and due(x)]
    later = [x["ref"] for x in mine if x["change"] == "later"]
    if met and not missed:
        return "achieved", met
    if later and not met and not annual:
        return "revised", later
    if missed and not met:
        return "failed", missed
    touched = [x["ref"] for x in labels if x["relation"] != "other" and due(x)]
    return ("unclear", touched) if touched else ("disappeared", [])


def propose_v2(promise: dict, evidence: list[dict], client: LLMClient, prompt: dict[str, str]) -> dict:
    """Judge v2: the model labels the evidence, `decide` names the outcome."""
    if not evidence:
        return {**_NOTHING, "labels": [], "annual": bool(promise["recurring"]), "model_outcome": None}
    obj, labels, complete = {}, [], False
    budget = 1500 + 60 * len(evidence)             # one label per statement, plus the model's reasoning
    for max_tokens in (budget, 2 * budget):        # an empty or cut-off reply gets one longer retry
        obj = _ask(promise, evidence, client, prompt, max_tokens=max_tokens)
        labels, complete = parse_labels(obj, evidence)
        if complete:
            break
    # the extraction's own flag counts too: either reading of "annual" makes a later year a renewal
    annual = bool(promise["recurring"]) or obj.get("annual") is True
    outcome, refs = ("unclear", [])                # a garbled reply settles nothing
    if complete:
        outcome, refs = decide(labels, annual, promise["target_year"])
    stated = str(obj.get("outcome", "")).strip().lower()
    return {"outcome": outcome, "rationale": str(obj.get("rationale") or "").strip(),
            "evidence_refs": refs, "parse_ok": complete, "labels": labels, "annual": annual,
            "model_outcome": stated if stated in OUTCOMES else None}


JUDGES = {"v1": propose, "v2": propose_v2}


def vote(outcomes: list[str]) -> str:
    """Strict majority over repeats, otherwise unclear: a verdict the judge does not reproduce is not one."""
    top, count = Counter(outcomes).most_common(1)[0]
    return top if count * 2 > len(outcomes) else "unclear"


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
    keeps a filled human sheet, judged "from the evidence shown", valid. `repeats` > 1 bypasses the
    response cache and takes the majority outcome.
    """
    if evidence_from is None:
        evidence_from = evidence_store.evidence_path(cfg, evidence)
        if not evidence_from.exists():             # before the cache is switched off for the repeats
            evidence_store.build(cfg, evidence)
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
