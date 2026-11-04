"""The promise-outcome judge: what became of a dated commitment, read from the evidence a retriever found.

Shared for the same reason the action classifier is shared: on RQ2 every retrieval arm is read by the
same judge with the same prompt and the same rule, so a difference between arms is a difference in what
was retrieved. Two versions:

- `v1` asks the model for the outcome directly (`configs/prompts/promise_outcome.md`). On the human
  check it over-committed: a verdict on 21 of the 35 promises the annotator called unclear.
- `v2` (default) asks the model only to label each evidence statement (is it about this very target,
  does it state the deadline year's result, does it move the commitment) and derives the outcome with a
  fixed rule, `decide`, that falls back to `unclear`. `configs/prompts/promise_outcome_v2.md`.
- `v3` keeps that design. Most of v2's errors on dev leave a settled promise `unclear` with the answer shown,
  so it adds labels the rule `decide_v3` may use, each of which can be switched off (`GW_JUDGE_V3_FEATURES`):
  a differently worded measure of the same commitment (`proxy`), a commitment stated to be part delivered
  (`partial`), and the deadline year's number compared with the target in code (`figure`). It also shows
  more of each statement (`GW_JUDGE_CHARS`), because tables were cut off.

The five-way label (`OUTCOMES`) is kept as detail; counts and agreement are reported on `REPORTED`,
where a re-dated commitment (`revised`) is a failed deadline (`reported`). Evidence rows carry
`ref` (E1, E2, ...), `year`, `page`, `text` and, where one statement comes right after the previous one
shown, `follows`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

from gw_common.llm import REPO_ROOT, LLMClient

PROMPTS = {
    "v1": REPO_ROOT / "configs" / "prompts" / "promise_outcome.md",
    "v2": REPO_ROOT / "configs" / "prompts" / "promise_outcome_v2.md",
    "v3": REPO_ROOT / "configs" / "prompts" / "promise_outcome_v3.md",
}
DEFAULT_JUDGE = "v2"
OUTCOMES = ("achieved", "failed", "revised", "unclear", "disappeared")
REPORTED = ("achieved", "failed", "unclear", "disappeared")
RELATIONS = ("this_target", "same_metric", "other")
RESULTS = ("met", "missed", "none")
CHANGES = ("later", "none")
EVIDENCE_CHARS = 500
V3_RELATIONS = ("this_target", "proxy", "same_metric", "other")
V3_RESULTS = ("met", "missed", "partial", "none")
V3_FEATURES = frozenset({"proxy", "partial", "figure"})
V3_CHARS = 1000
_LEVELS = ("achieve", "maintain")  # a target stated as a level; "reduce by" is not comparable with a figure
_JSON = re.compile(r"\{.*\}", re.S)


def v3_features() -> frozenset[str]:
    raw = os.getenv("GW_JUDGE_V3_FEATURES")
    if raw is None:
        return V3_FEATURES
    return frozenset(f.strip() for f in raw.split(",") if f.strip()) & V3_FEATURES


def v3_chars() -> int:
    return int(os.getenv("GW_JUDGE_CHARS") or V3_CHARS)


def reported(outcome: str) -> str:
    """The outcome as it is reported: a re-dated commitment (`revised`) is a failed deadline.

    The deadline passed without the target being reported as met, whether the report admits the miss
    or moves the date. Where the line between the two falls was not drawn the same way by the annotator
    across two rounds or by the judge (`docs/promises.md`, section 7), so counts, shares and agreement
    are reported on `REPORTED`; the five-way label is kept as detail.
    """
    return "failed" if outcome == "revised" else outcome


def where(e: dict) -> str:
    """'2024 report, p.9' and, when the statement comes right after the previous one shown, that too."""
    follows = f", directly follows {e['follows']}" if e.get("follows") else ""
    return f"{e['year']} report, p.{e['page']}{follows}"


def sections(path: Path) -> dict[str, str]:
    """The `## system` and `## user` parts of a prompt file."""
    parts = re.split(r"^## (system|user)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def describe(judge: str = DEFAULT_JUDGE) -> dict:
    """What the run manifest records about the judge."""
    path = PROMPTS[judge]
    info = {
        "judge": judge,
        "prompt": path.name,
        "prompt_sha": hashlib.sha256(path.read_bytes()).hexdigest()[:12],
        "rule": {"v1": "model", "v2": "decide", "v3": "decide_v3"}[judge],
    }
    if judge == "v3":
        info.update(features=sorted(v3_features()), evidence_chars=v3_chars())
    return info


def _target_phrase(p: dict) -> tuple[str, str]:
    quantity = ""
    if p.get("quantity") is not None:
        number = int(p["quantity"]) if float(p["quantity"]).is_integer() else p["quantity"]
        quantity = f" — {p.get('direction') or 'target'} {number}{p.get('unit') or ''}"
    baseline = f" (baseline {p['baseline_year']})" if p.get("baseline_year") else ""
    return quantity, baseline


def _ask(
    promise: dict,
    evidence: list[dict],
    client: LLMClient,
    prompt: dict[str, str],
    max_tokens: int,
    chars: int = EVIDENCE_CHARS,
) -> dict:
    quantity, baseline = _target_phrase(promise)
    block = "\n".join(f"[{e['ref']}] ({where(e)}) {e['text'][:chars]}" for e in evidence)
    origin = promise["origin"]
    user = prompt["user"].format(
        company=promise["company"],
        origin_year=origin["year"],
        origin_page=origin.get("page"),
        origin_text=(origin.get("text") or origin.get("target_text") or "")[:700],
        metric=promise["metric"],
        quantity=quantity,
        baseline=baseline,
        target_year=promise["target_year"],
        evidence=block,
        recurring=" (RECURRING annual target)" if promise.get("recurring") else "",
    )
    reply = client.chat(
        [{"role": "system", "content": prompt["system"]}, {"role": "user", "content": user}],
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    match = _JSON.search(reply.text or "")
    try:
        obj = json.loads(match.group(0)) if match else {}
    except ValueError:
        obj = {}
    return obj if isinstance(obj, dict) else {}


_NOTHING = {
    "outcome": "disappeared",
    "rationale": "No statements were retrieved for the deadline years.",
    "evidence_refs": [],
    "parse_ok": True,
}


def propose(promise: dict, evidence: list[dict], client: LLMClient, prompt: dict[str, str]) -> dict:
    """Judge v1: the model names the outcome."""
    if not evidence:
        return dict(_NOTHING)
    obj = _ask(promise, evidence, client, prompt, max_tokens=600)
    outcome = str(obj.get("outcome", "")).strip().lower()
    refs = [str(r).strip("[] ").upper() for r in obj.get("evidence", []) if isinstance(r, str)]
    valid = {e["ref"] for e in evidence}
    return {
        "outcome": outcome if outcome in OUTCOMES else "unclear",
        "rationale": str(obj.get("rationale") or "").strip(),
        "evidence_refs": [r for r in refs if r in valid],
        "parse_ok": outcome in OUTCOMES,
    }


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
        labels.append(
            {
                "ref": e["ref"],
                "year": e.get("year"),
                "relation": relation,
                "deadline_result": result if mine and result in RESULTS else "none",
                "change": change if mine and change in CHANGES else "none",
            }
        )
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

    def due(x: dict) -> bool:  # from a report of the deadline year or later
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
        return {**_NOTHING, "labels": [], "annual": bool(promise.get("recurring")), "model_outcome": None}
    obj, labels, complete = {}, [], False
    budget = 1500 + 60 * len(evidence)  # one label per statement, plus the model's reasoning
    for max_tokens in (budget, 2 * budget):  # an empty or cut-off reply gets one longer retry
        obj = _ask(promise, evidence, client, prompt, max_tokens=max_tokens)
        labels, complete = parse_labels(obj, evidence)
        if complete:
            break
    # the extraction's own flag counts too: either reading of "annual" makes a later year a renewal
    annual = bool(promise.get("recurring")) or obj.get("annual") is True
    outcome, refs = ("unclear", [])  # a garbled reply settles nothing
    if complete:
        outcome, refs = decide(labels, annual, promise["target_year"])
    stated = str(obj.get("outcome", "")).strip().lower()
    return {
        "outcome": outcome,
        "rationale": str(obj.get("rationale") or "").strip(),
        "evidence_refs": refs,
        "parse_ok": complete,
        "labels": labels,
        "annual": annual,
        "model_outcome": stated if stated in OUTCOMES else None,
    }


def parse_labels_v3(obj: dict, evidence: list[dict]) -> tuple[list[dict], bool]:
    """As `parse_labels`, with the added labels. A result stands on this_target or proxy, a change on
    this_target only, and a figure on any statement about the metric."""
    given = {}
    for item in obj.get("evidence") or []:
        if isinstance(item, dict):
            given[str(item.get("ref", "")).strip("[] ").upper()] = item
    labels, complete = [], isinstance(obj.get("annual"), bool)
    for e in evidence:
        raw = given.get(e["ref"], {})
        relation = str(raw.get("relation", "")).strip().lower()
        if relation not in V3_RELATIONS:
            relation, complete = "other", False
        result = str(raw.get("deadline_result", "")).strip().lower()
        change = str(raw.get("change", "")).strip().lower()
        figure = raw.get("figure") if relation != "other" else None
        labels.append(
            {
                "ref": e["ref"],
                "year": e.get("year"),
                "relation": relation,
                "deadline_result": result
                if relation in ("this_target", "proxy") and result in V3_RESULTS
                else "none",
                "change": change if relation == "this_target" and change in CHANGES else "none",
                "figure": figure if isinstance(figure, dict) else None,
            }
        )
    return labels, complete


def _unit(text: object) -> str:
    return re.sub(r"\s+", "", str(text or "").lower()).replace("³", "3").replace("²", "2")


def figure_result(figure: dict | None, promise: dict, better: str | None) -> str:
    """The deadline year's number against the target: met, missed, or none when they cannot be compared.

    Only a target stated as a level, in the same unit, with a known good direction. Anything else is left to
    the statement's own words, so a share cannot be read against an amount."""
    target = promise.get("quantity")
    if (
        figure is None
        or target is None
        or better not in ("lower", "higher")
        or promise.get("direction") not in _LEVELS
        or not _unit(promise.get("unit"))
        or _unit(figure.get("unit")) != _unit(promise.get("unit"))
    ):
        return "none"
    try:
        value = float(figure["value"])
    except (KeyError, TypeError, ValueError):
        return "none"
    good = value <= float(target) if better == "lower" else value >= float(target)
    return "met" if good else "missed"


def decide_v3(
    labels: list[dict],
    annual: bool,
    promise: dict,
    better: str | None = None,
    features: frozenset[str] = V3_FEATURES,
) -> tuple[str, list[str], list[str]]:
    """The outcome, the statements it rests on, and which added features it needed; `decide`'s order and
    calendar otherwise, and with no features it reads the labels as `decide` would.

    A partial delivery counts as a miss: the deadline passed without the target reported as met (the reporting
    convention, `docs/promises.md` section 7). A figure speaks only where the statement's words did not."""
    deadline = promise.get("target_year")

    def due(x: dict) -> bool:
        return deadline is None or x.get("year") is None or x["year"] >= deadline

    met, missed, later = [], [], []
    for x in labels:
        result, how = "none", None
        if x["relation"] == "this_target" or (x["relation"] == "proxy" and "proxy" in features):
            result = x["deadline_result"]
            how = "proxy" if x["relation"] == "proxy" else None
            if result == "partial":
                result = "missed" if "partial" in features else "none"
                how = "partial"
        if result == "none" and "figure" in features and x["relation"] != "other" and due(x):
            result = figure_result(x.get("figure"), promise, better)
            how = "figure"
        if result == "met" and (due(x) or not annual):
            met.append((x["ref"], how))
        elif result == "missed" and due(x):
            missed.append((x["ref"], how))
        if x["relation"] == "this_target" and x["change"] == "later":
            later.append(x["ref"])

    def basis(found: list[tuple[str, str | None]]) -> list[str]:
        """The added features a verdict needed: none when the commitment's own words also say so."""
        return [] if any(how is None for _, how in found) else sorted({how for _, how in found})

    if met and not missed:
        return "achieved", [r for r, _ in met], basis(met)
    if later and not met and not annual:
        return "revised", later, []
    if missed and not met:
        return "failed", [r for r, _ in missed], basis(missed)
    touched = [x["ref"] for x in labels if x["relation"] != "other" and due(x)]
    return ("unclear", touched, []) if touched else ("disappeared", [], [])


def propose_v3(promise: dict, evidence: list[dict], client: LLMClient, prompt: dict[str, str]) -> dict:
    """Judge v3: the model labels the evidence, `decide_v3` names the outcome."""
    if not evidence:
        return {**_NOTHING, "labels": [], "annual": bool(promise.get("recurring")), "better": None,
                "model_outcome": None, "basis": []}
    obj, labels, complete = {}, [], False
    budget = 1500 + 90 * len(evidence)  # one label and one figure per statement, plus the model's reasoning
    chars = v3_chars()
    for max_tokens in (budget, 2 * budget):
        obj = _ask(promise, evidence, client, prompt, max_tokens=max_tokens, chars=chars)
        labels, complete = parse_labels_v3(obj, evidence)
        if complete:
            break
    annual = bool(promise.get("recurring")) or obj.get("annual") is True
    better = str(obj.get("better") or "").strip().lower() or None
    outcome, refs, basis = "unclear", [], []
    if complete:
        outcome, refs, basis = decide_v3(labels, annual, promise, better, v3_features())
    stated = str(obj.get("outcome", "")).strip().lower()
    return {
        "outcome": outcome,
        "rationale": str(obj.get("rationale") or "").strip(),
        "evidence_refs": refs,
        "parse_ok": complete,
        "labels": labels,
        "annual": annual,
        "better": better,
        "basis": basis,
        "model_outcome": stated if stated in OUTCOMES else None,
    }


JUDGES = {"v1": propose, "v2": propose_v2, "v3": propose_v3}


def vote(outcomes: list[str]) -> str:
    """Strict majority over repeats, otherwise unclear: a verdict the judge does not reproduce is not one."""
    top, count = Counter(outcomes).most_common(1)[0]
    return top if count * 2 > len(outcomes) else "unclear"


def judge(
    promise: dict,
    evidence: list[dict],
    client: LLMClient,
    version: str = DEFAULT_JUDGE,
    prompt: dict[str, str] | None = None,
) -> dict:
    """One judgement of one promise on one evidence list, by the named judge version."""
    return JUDGES[version](promise, evidence, client, prompt or sections(PROMPTS[version]))
