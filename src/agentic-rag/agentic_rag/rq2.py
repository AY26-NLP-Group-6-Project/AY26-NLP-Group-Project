"""RQ2: gather what would settle a dated commitment, whichever way it falls.

Hop 0 makes no LLM call: every report in the window has a budget, the first report at or after the deadline
the largest, and the statements next to its two best hits are added, the trajectory finder's rules over the
shared statement store. `AGENTIC_MAX_HOPS=0` stops there, which is what the agent's gain is measured against.

With hops, one fixed search first looks for a moved or dropped deadline: stopping on a statement that looks
like success would otherwise leave the contrary one unread, and the judge's rule needs both. Then the planner
reads what has been gathered and asks for more where the deadline-year result, a change, or a report of the
window is missing: a search in the report's own terms, the statements around one already shown (a table's
result sits beside its target), or the whole page. It never names an outcome; the shared judge does.

Evidence the agent found has its own slots (`AGENT_SLOTS` of the cap), so it cannot be crowded out by hop 0.
"""

from __future__ import annotations

import time

from gw_common.eval.rq2 import evidence_of
from gw_common.evidence import normalise
from gw_common.judges.promise import where
from gw_common.schemas import EvidenceSpan, Query

from agentic_rag.tools import Fence

DEFAULT_HOPS = 2
K_DEADLINE = 6          # the first report at or after the deadline, where the outcome should be reported
K_AFTER = 3             # each report after that
K_BEFORE = 2            # each report between the promise and the deadline
NEIGHBOURS_OF = 2       # hits of the deadline report whose adjacent statements are added
AGENT_SLOTS = 8         # of the cap, kept for statements a later hop found
ACTIONS_PER_HOP = 3
SEARCH_K = 4            # statements per search
PAGE_K = 6              # statements taken from an opened page, nearest the statement it was opened from
SHOW_CHARS = 300
CHANGE_TERMS = "postponed delayed extended revised deferred new target date"
_MODES = {"keyword": "bm25", "meaning": "hybrid"}


def _target_line(p: dict) -> str:
    quantity = ""
    if p.get("quantity") is not None:
        number = int(p["quantity"]) if float(p["quantity"]).is_integer() else p["quantity"]
        quantity = f" — {p.get('direction') or 'target'} {number}{p.get('unit') or ''}"
    baseline = f" (baseline {p['baseline_year']})" if p.get("baseline_year") else ""
    recurring = " (recurring annual target)" if p.get("recurring") else ""
    return f"{p['metric']}{quantity}{baseline}{recurring}"


class Pool:
    """Statements in the order they were found, one per (year, text)."""

    def __init__(self) -> None:
        self.spans: dict[str, EvidenceSpan] = {}
        self._seen: set[tuple[int, str]] = set()

    def add(self, spans: list[EvidenceSpan], why: str) -> int:
        added = 0
        for s in spans:
            key = (s.year, normalise(s.text))
            if key not in self._seen and s.text.strip():
                self._seen.add(key)
                self.spans[s.statement_id] = s.model_copy(update={"why": why})
                added += 1
        return added

    def final(self, k: int) -> list[EvidenceSpan]:
        """Up to `k`: what later hops found up to its slots, the rest from hop 0 in its order of priority."""
        first = [s for s in self.spans.values() if s.why.startswith("agent:hop0")]
        later = [s for s in self.spans.values() if not s.why.startswith("agent:hop0")]
        room_later = min(len(later), max(AGENT_SLOTS, k - len(first)))
        return (first[: k - room_later] + later[:room_later])[:k]


def hop_zero(fence: Fence, query: Query, deadline: int, pool: Pool) -> None:
    years = fence.years()
    outcome_year = next((y for y in years if y >= deadline), None)
    # the report that should carry the outcome first, so the cap never cuts into it
    for year in sorted(years, key=lambda y: (y != outcome_year, y < deadline, y)):
        budget = K_DEADLINE if year == outcome_year else K_AFTER if year > deadline else K_BEFORE
        hits = fence.search(query.text, year=year, k=budget, mode="hybrid")
        pool.add(hits, "agent:hop0:retrieved")
        if year == outcome_year:
            for hit in hits[:NEIGHBOURS_OF]:
                pool.add(fence.around(hit.statement_id), "agent:hop0:neighbour")


def apply_action(action: dict, rows: dict[str, dict], fence: Fence, pool: Pool, tried: list[str],
                 hop: int) -> int:
    """One planner action, fenced; how many new statements it brought."""
    tool = str(action.get("tool", "")).strip().lower()
    if tool == "search":
        text = str(action.get("query") or "").strip()
        if not text or normalise(text) in {normalise(q) for q in tried}:
            return 0
        tried.append(text)
        year = action.get("year") if isinstance(action.get("year"), int) else None
        mode = _MODES.get(str(action.get("mode", "")).strip().lower(), "hybrid")
        return pool.add(fence.search(text, year=year, k=SEARCH_K, mode=mode), f"agent:hop{hop}:search")
    row = rows.get(str(action.get("ref", "")).strip("[] ").upper())
    if row is None:
        return 0
    if tool == "around":
        return pool.add(fence.around(row["stmt_id"], before=2, after=2), f"agent:hop{hop}:around")
    if tool == "page":
        spans = fence.page(row["year"], row["page"])
        at = next((i for i, s in enumerate(spans) if s.statement_id == row["stmt_id"]), 0)
        near = sorted(range(len(spans)), key=lambda i: abs(i - at))[:PAGE_K]
        return pool.add([spans[i] for i in sorted(near)], f"agent:hop{hop}:page")
    return 0


def run(agent, query: Query, k: int, trace, started: float) -> list[EvidenceSpan]:
    hops = agent.hops_for(DEFAULT_HOPS)
    promise = query.meta["promise"]
    deadline = promise["target_year"]
    fence = Fence(agent.corpus, query)
    pool = Pool()
    hop_zero(fence, query, deadline, pool)
    trace.stop = "hop0"
    if hops == 0:
        return pool.final(k)

    tried = [query.text, f"{promise['metric']} {CHANGE_TERMS}"]
    pool.add(fence.search(tried[-1], k=SEARCH_K, mode="bm25"), "agent:probe")
    origin = promise["origin"]
    years = fence.years()
    trace.stop = "max_hops"
    for hop in range(1, hops + 1):
        if time.perf_counter() - started > agent.timeout_s:
            trace.stop = "timeout"
            break
        rows = evidence_of(pool.final(k))
        evidence = "\n".join(f"[{r['ref']}] ({where(r)}) {r['text'][:SHOW_CHARS]}" for r in rows) or "(none)"
        reply = agent.ask("rq2_plan", agent.prompts["rq2_plan"]["user"].format(
            company=promise["company"], origin_year=origin["year"], origin_page=origin.get("page"),
            origin_text=(origin.get("text") or origin.get("target_text") or "")[:700],
            target=_target_line(promise), target_year=deadline, years=", ".join(map(str, years)),
            tried="\n".join(f"- {q}" for q in tried), evidence=evidence, hop=hop, max_hops=hops,
            max_actions=ACTIONS_PER_HOP), trace)
        if reply is None:
            break
        raw = reply.get("actions")
        actions = [a for a in raw if isinstance(a, dict)][:ACTIONS_PER_HOP] if isinstance(raw, list) else []
        by_ref = {r["ref"]: r for r in rows}
        brought = [apply_action(a, by_ref, fence, pool, tried, hop) for a in actions]
        trace.steps.append({"hop": hop, "missing": reply.get("missing"),
                            "result_seen": reply.get("result_seen"),
                            "change_seen": reply.get("change_seen"), "stop": reply.get("stop"),
                            "actions": actions, "brought": brought})
        if not actions or reply.get("stop") is True and not sum(brought):
            trace.stop = "planner_stop"
            break
        if not sum(brought):
            trace.stop = "nothing_new"
            break
    return pool.final(k)
