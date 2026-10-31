"""RQ1: retrieve only when the sentence cannot be read alone, and only what closes the gap.

Three findings set this policy (`docs/results.md`). The classifier cites retrieved evidence on 1-9 % of
items, because the sentence usually carries the answer. A minority of retrieved statements are relevant.
And evidence costs something where nothing was missing: same-report evidence takes `none` F1 from 0.766
to 0.690. So the first planner call is a gate: a sentence with no gap gets no evidence, and the classifier
then reads exactly what `sentence_only` reads.

Where there is a gap the planner states it as a question. Hop by hop it searches, and a verifier call says
which passages answer the question. Two ways to choose the final spans, both compared on dev:

    verified  only passages the verifier says answer the question, cross-encoder order; possibly none
    rerank    the top k of everything found, by the cross-encoder against the question, not the sentence

`hops` counts planner calls: 1 is the gate and one search with `rerank` selection; 2 adds the verifier;
3 lets the verifier ask for one more search.
"""

from __future__ import annotations

import time

from gw_common.evidence import normalise
from gw_common.schemas import EvidenceSpan, Query

from agentic_rag.tools import Fence

DEFAULT_HOPS = 2
MAX_GAPS = 3
QUERIES_PER_HOP = 2
SEARCH_K = 5         # statements per query
SHOW_SPANS = 6       # passages the verifier reads
SHOW_CHARS = 300     # characters per passage


def gaps_of(reply: dict) -> list[dict]:
    gaps = reply.get("gaps")
    if not isinstance(gaps, list):
        return []
    return [g for g in gaps if isinstance(g, dict) and g.get("question")][:MAX_GAPS]


def queries_of(reply: dict, tried: list[str]) -> list[str]:
    raw = reply.get("queries")
    seen = {normalise(q) for q in tried}
    out = []
    for q in raw if isinstance(raw, list) else []:
        q = str(q).strip()
        if q and normalise(q) not in seen:
            seen.add(normalise(q))
            out.append(q)
    return out[:QUERIES_PER_HOP]


def _rank(agent, question: str, pool: dict[str, EvidenceSpan]) -> list[EvidenceSpan]:
    spans = list(pool.values())
    if not spans:
        return []
    scores = agent.reranker.rerank(question, [s.text for s in spans])
    return [s for _, s in sorted(zip(scores, spans, strict=True), key=lambda kv: -kv[0])]


def run(agent, query: Query, k: int, trace, started: float) -> list[EvidenceSpan]:
    hops = agent.hops_for(DEFAULT_HOPS)
    fence = Fence(agent.corpus, query)
    target = query.target_text or query.text
    aspect = query.aspect or "(none proposed)"
    gate = agent.ask("rq1_gate", agent.prompts["rq1_gate"]["user"].format(
        company=query.company, year=query.anchor_year, aspect=aspect, text=target), trace)
    if gate is None:
        return []                        # no reading of the sentence: fall back to the sentence alone
    gaps = gaps_of(gate)
    trace.steps.append({"hop": 1, "gaps": gaps, "queries": gate.get("queries")})
    if not gaps:
        trace.stop = "no_gap"
        return []

    question = " ".join(str(g["question"]) for g in gaps)
    pool: dict[str, EvidenceSpan] = {}

    def add(spans: list[EvidenceSpan], hop: int) -> None:
        seen = {normalise(s.text) for s in pool.values()}
        for s in spans:
            if normalise(s.text) not in seen:
                seen.add(normalise(s.text))
                pool[s.statement_id] = s.model_copy(update={"why": f"agent:hop{hop}"})

    tried = queries_of(gate, [])
    add(fence.around_target(), 1)
    for q in tried:
        add(fence.search(q, k=SEARCH_K), 1)

    verified: list[str] | None = None
    trace.stop = "max_hops"
    for hop in range(2, hops + 1):
        if time.perf_counter() - started > agent.timeout_s:
            trace.stop = "timeout"
            break
        if not pool:
            trace.stop = "nothing_found"
            break
        shown = _rank(agent, question, pool)[:SHOW_SPANS]
        passages = "\n".join(f"[P{i}] ({s.year}, p.{s.page}) {s.text[:SHOW_CHARS]}"
                             for i, s in enumerate(shown, 1))
        gap_lines = "\n".join(f"- {g.get('kind', 'gap')}: {g['question']}" for g in gaps)
        reply = agent.ask("rq1_verify", agent.prompts["rq1_verify"]["user"].format(
            company=query.company, year=query.anchor_year, aspect=aspect, text=target, gaps=gap_lines,
            passages=passages, more="yes" if hop < hops else "no"), trace)
        if reply is None:
            break
        refs = reply.get("answers") if isinstance(reply.get("answers"), list) else []
        found = {str(r).strip("[] ").upper() for r in refs}
        verified = [s.statement_id for i, s in enumerate(shown, 1) if f"P{i}" in found]
        new = queries_of(reply, tried) if hop < hops else []
        trace.steps.append({"hop": hop, "answers": sorted(found), "resolved": reply.get("resolved"),
                            "queries": new})
        if reply.get("resolved") is True or verified and not new:
            trace.stop = "resolved"
            break
        if not new:
            trace.stop = "unresolved"
            break
        tried += new
        for q in new:
            add(fence.search(q, k=SEARCH_K), hop)

    ranked = _rank(agent, question, pool)
    if agent.select == "verified" and hops >= 2:
        keep = set(verified or [])
        ranked = [s for s in ranked if s.statement_id in keep]
    return ranked[:k]
