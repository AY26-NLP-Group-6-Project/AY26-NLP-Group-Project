"""Bounded plan-retrieve-stop retriever for the `cross_year_agentic` condition.

Hop 0 is the ordinary search with the sentence itself (no LLM). Each later hop asks the planner
(`configs/prompts/agentic_planner.md`) whether the evidence gathered so far resolves the sentence's
references and actor; if not, it proposes keyword queries, optionally restricted to earlier or later
reports, which run through the same search. The agent plans and rewrites; it does not pick the final
spans. Those come from reciprocal rank fusion over every ranked list it produced (or, with
`AGENTIC_SELECT=rerank`, from the cross-encoder against the original sentence), because arXiv
2601.07711 finds agents worse than a reranker at final document selection.

Every knob that sets the budget is read from the environment, so a budget sweep is a loop over env
values with the same code:

    AGENTIC_MAX_HOPS        planner calls per item at most (0 = plain search, no LLM)    default 2
    AGENTIC_QUERIES_PER_HOP rewritten queries run per hop                                 default 2
    AGENTIC_TIMEOUT_S       no new hop starts after this many seconds per item            default 60
    AGENTIC_BASE_MODE       bm25 | bm25+rerank | rrf | rrf+rerank (rrf needs EMB_API_KEY) default auto
    AGENTIC_SELECT          rrf | rerank                                                  default rrf

The agent's own chat tokens are recorded per item in `traces`, so the system can charge them to the
prediction (the harness only counts the classifier's tokens and the retriever's embedding tokens).
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from baseline_rag.index import CANDIDATES, RERANK_DEPTH, CrossEncoderReranker, rrf
from baseline_rag.retrieve import HybridRetriever
from gw_common.evidence import is_target_span, normalise
from gw_common.llm import REPO_ROOT, LLMClient
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query

PROMPT = REPO_ROOT / "configs" / "prompts" / "agentic_planner.md"
TRACE_FILE = REPO_ROOT / "artifacts" / "agentic" / "traces.jsonl"
BASE_MODES = ("bm25", "bm25+rerank", "rrf", "rrf+rerank")
SELECT_MODES = ("rrf", "rerank")
SHOW_SPANS = 4       # evidence the planner sees per hop
SHOW_CHARS = 300     # characters per span shown to the planner
LIST_DEPTH = 10      # ranked list kept per query before fusion
_JSON_RE = re.compile(r"\{.*\}", re.S)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


def _sections(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## (system|user)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def trace_key(company: str | None, year: int | None, text: str | None) -> tuple:
    """How a trace written at retrieval time is found again at classification time."""
    return (company or "", year, normalise(text or ""))


@dataclass(slots=True)
class Plan:
    sufficient: bool
    queries: list[str]
    years: str = "any"
    need: str = ""
    parse_ok: bool = True


def parse_plan(text: str) -> Plan:
    """A reply that is not the asked JSON stops the loop (sufficient=True) rather than guessing queries."""
    match = _JSON_RE.search(text or "")
    if match:
        try:
            obj = json.loads(match.group(0))
            queries = obj.get("queries") or []
            queries = [str(q).strip() for q in (queries if isinstance(queries, list) else [queries])]
            years = str(obj.get("years") or "any").strip().lower()
            return Plan(sufficient=bool(obj.get("sufficient")), queries=[q for q in queries if q],
                        years=years if years in ("earlier", "later") else "any",
                        need=str(obj.get("need") or "").strip())
        except (ValueError, TypeError, AttributeError):
            pass
    return Plan(sufficient=True, queries=[], parse_ok=False)


@dataclass(slots=True)
class Trace:
    company: str
    year: int | None
    target: str
    hops: int = 0                 # planner calls made
    llm_calls: int = 0            # planner calls that reached the model (not cached)
    input_tokens: int = 0
    output_tokens: int = 0
    planner_ms: float = 0.0
    stop: str = ""                # sufficient | max_hops | timeout | parse_error | llm_error | no_new_query
    steps: list[dict] = field(default_factory=list)


class AgenticRetriever:
    def __init__(self, build_id: str = "dev", client: LLMClient | None = None) -> None:
        self.max_hops = _env_int("AGENTIC_MAX_HOPS", 2)
        self.queries_per_hop = _env_int("AGENTIC_QUERIES_PER_HOP", 2)
        self.timeout_s = float(os.getenv("AGENTIC_TIMEOUT_S", "") or 60)
        default_mode = "rrf+rerank" if os.getenv("EMB_API_KEY", "").strip() else "bm25+rerank"
        self.base_mode = os.getenv("AGENTIC_BASE_MODE", "").strip() or default_mode
        self.select = os.getenv("AGENTIC_SELECT", "").strip() or "rrf"
        if self.base_mode not in BASE_MODES:
            raise ValueError(f"AGENTIC_BASE_MODE must be one of {BASE_MODES}")
        if self.select not in SELECT_MODES:
            raise ValueError(f"AGENTIC_SELECT must be one of {SELECT_MODES}")

        self.client = client or LLMClient()   # one client: the harness reads its embedding usage
        # The shared passage store, filters and BM25/dense indexes, as-is; ranking is done here.
        self.store = HybridRetriever(build_id, "rrf" if self.base_mode.startswith("rrf") else "bm25",
                                     client=self.client)
        self.chunks = self.store.chunks
        need_reranker = self.base_mode.endswith("rerank") or self.select == "rerank"
        self.reranker = CrossEncoderReranker() if need_reranker else None
        self._prompt = _sections(PROMPT)
        self.traces: dict[tuple, Trace] = {}
        self._lock = threading.Lock()

    def describe(self) -> dict[str, object]:
        return {"max_hops": self.max_hops, "queries_per_hop": self.queries_per_hop,
                "timeout_s": self.timeout_s, "base_mode": self.base_mode, "select": self.select,
                "planner_prompt": PROMPT.name}

    # ------------------------------------------------------------------ search
    def _allowed(self, query: Query, years: str = "any") -> set[int] | None:
        allowed = self.store._allowed(query)
        if allowed is None or years == "any" or query.anchor_year is None:
            return allowed
        later = years == "later"
        narrowed = {i for i in allowed
                    if (self.chunks[i].year > query.anchor_year) == later
                    and self.chunks[i].year != query.anchor_year}
        return narrowed or allowed   # no report on that side: fall back rather than return nothing

    def _ranked(self, text: str, allowed: set[int] | None) -> list[tuple[int, float]]:
        if self.base_mode.startswith("rrf"):
            ranked = rrf(self.store.bm25.search(text, allowed, CANDIDATES),
                         self.store._dense_search(text, allowed))
        else:
            ranked = self.store.bm25.search(text, allowed, CANDIDATES)
        if self.base_mode.endswith("rerank") and ranked:
            head = ranked[:RERANK_DEPTH]
            scores = self.reranker.rerank(text, [self.chunks[i].text for i, _ in head])
            ranked = sorted(zip([i for i, _ in head], scores, strict=True), key=lambda kv: -kv[1])
        return ranked[:LIST_DEPTH]

    def _fuse(self, lists: list[tuple[int, str, list[tuple[int, float]]]], query: Query,
              original: str, k: int) -> list[EvidenceSpan]:
        """Fused, de-duplicated spans without the target; `why` names the hop that first found each."""
        found_at: dict[int, int] = {}
        for hop, _q, ranked in lists:
            for i, _ in ranked:
                found_at.setdefault(i, hop)
        if self.select == "rerank" and found_at:
            pool = list(found_at)[:RERANK_DEPTH * 2]
            scores = self.reranker.rerank(original, [self.chunks[i].text for i in pool])
            fused = sorted(zip(pool, scores, strict=True), key=lambda kv: -kv[1])
        else:
            fused = rrf(*[ranked for _hop, _q, ranked in lists])
        out, seen = [], set()
        for i, score in fused:
            c = self.chunks[i]
            key = normalise(c.text)
            if key in seen:
                continue
            seen.add(key)
            span = EvidenceSpan(statement_id=c.chunk_id, text=c.text, company=c.company, year=c.year,
                                page=c.page, file=c.file, score=round(float(score), 4),
                                why=f"agent:hop{found_at[i]}")
            if is_target_span(span, query):
                continue
            out.append(span)
            if len(out) >= k:
                break
        return out

    # ------------------------------------------------------------------ planner
    def _plan(self, query: Query, shown: list[EvidenceSpan], tried: list[str], hop: int):
        evidence = "\n".join(f"- ({s.year}, p.{s.page}) {s.text[:SHOW_CHARS]}" for s in shown) or "(none)"
        user = self._prompt["user"].format(
            company=query.company or "(not given)", year=query.anchor_year or "(not given)",
            aspect=query.aspect or "(none proposed)", text=query.target_text or query.text,
            tried="\n".join(f"- {q}" for q in tried), evidence=evidence, hop=hop,
            max_hops=self.max_hops, max_queries=self.queries_per_hop)
        messages = [{"role": "system", "content": self._prompt["system"]}, {"role": "user", "content": user}]
        return self.client.chat(messages, max_tokens=512)

    # ------------------------------------------------------------------ protocol
    def retrieve(self, query: Query, *, k: int = 3) -> list[EvidenceSpan]:
        allowed = self._allowed(query)
        if allowed is not None and not allowed:
            return []
        original = f"{query.aspect}. {query.text}" if query.aspect else query.text
        lists = [(0, original, self._ranked(original, allowed))]
        if query.condition is not EvidenceCondition.CROSS_YEAR_AGENTIC:
            return self._fuse(lists, query, original, k)   # the in-system non-agentic arms: one search

        trace = Trace(company=query.company or "", year=query.anchor_year, target=query.target_text or "")
        tried, t0 = [original], time.perf_counter()
        trace.stop = "max_hops"
        for hop in range(1, self.max_hops + 1):
            if time.perf_counter() - t0 > self.timeout_s:
                trace.stop = "timeout"
                break
            shown = self._fuse(lists, query, original, SHOW_SPANS)
            try:
                reply = self._plan(query, shown, tried, hop)
            except Exception as exc:  # noqa: BLE001 - a failed planner call ends the loop, not the run
                trace.stop = "llm_error"
                trace.steps.append({"hop": hop, "error": str(exc)[:200]})
                break
            trace.hops += 1
            trace.llm_calls += 0 if reply.cached else 1
            trace.input_tokens += reply.input_tokens
            trace.output_tokens += reply.output_tokens
            trace.planner_ms += reply.latency_ms
            plan = parse_plan(reply.text)
            new = [q for q in plan.queries if normalise(q) not in {normalise(t) for t in tried}]
            new = new[: self.queries_per_hop]
            trace.steps.append({"hop": hop, "sufficient": plan.sufficient, "need": plan.need,
                                "queries": new, "years": plan.years, "parse_ok": plan.parse_ok})
            if not plan.parse_ok:
                trace.stop = "parse_error"
                break
            if plan.sufficient:
                trace.stop = "sufficient"
                break
            if not new:
                trace.stop = "no_new_query"
                break
            hop_allowed = self._allowed(query, plan.years)
            for q in new:
                tried.append(q)
                lists.append((hop, q, self._ranked(q, hop_allowed)))

        spans = self._fuse(lists, query, original, k)
        trace.steps.append({"final": [s.why for s in spans]})
        with self._lock:
            self.traces[trace_key(query.company, query.anchor_year, query.target_text)] = trace
        self._write_trace(trace)
        return spans

    def _write_trace(self, trace: Trace) -> None:
        TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, TRACE_FILE.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), **self.describe(),
                                 **asdict(trace)}, ensure_ascii=False) + "\n")
