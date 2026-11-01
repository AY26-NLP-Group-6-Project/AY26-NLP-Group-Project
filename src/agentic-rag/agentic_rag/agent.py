"""A bounded planner over the corpus tools, one retriever for both research questions.

What the loop owns: the budget (`AGENTIC_MAX_HOPS`, `AGENTIC_TIMEOUT_S`), the planner calls and their
accounting, the per-item trace. What each question owns is in `rq1.py` and `rq2.py`: when to search, what
the planner is asked, and how the final evidence is chosen. The agent only gathers evidence; the shared
classifier and the shared judge read what comes back, unchanged, under the same budget as every other arm.

Why the first version was replaced: over the passage store it spent 3.2× the plain search and 95 % of the
evidence it handed over was what hop 0 had found anyway (839 of 879 spans,
`results/agent-rag/passage-hybrid` on the branch `dev/luyuanzhi`), because rank fusion gave the first
search's list the three slots. Evidence found by a later query now has room of its own.

Environment:

    AGENTIC_MAX_HOPS   planner calls per item at most; 0 is the fixed search, no LLM   default per question
    AGENTIC_TIMEOUT_S  no new planner call after this many seconds per item            default 90
    AGENTIC_SELECT     rq1 only: verified | rerank | neighbours (see rq1.py)           default verified
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from baseline_rag.chunks import DEFAULT_BUILD
from baseline_rag.index import CrossEncoderReranker
from gw_common import corpus as corpus_tools
from gw_common.evidence import normalise
from gw_common.judges.promise import sections
from gw_common.llm import REPO_ROOT, LLMClient
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query

PROMPT_DIR = REPO_ROOT / "configs" / "prompts"
TRACE_DIR = REPO_ROOT / "artifacts" / "agentic"
PROMPTS = {"rq1_gate": "agentic_rq1_gate.md", "rq1_verify": "agentic_rq1_verify.md",
           "rq2_plan": "agentic_rq2_planner.md"}
PLAN_TOKENS = 1500      # the reply plus the model's reasoning; an empty or cut-off reply gets a longer retry
_JSON_RE = re.compile(r"\{.*\}", re.S)
_AGENT_CONDITIONS = (EvidenceCondition.CROSS_YEAR_AGENTIC, EvidenceCondition.COMPANY_AGENTIC,
                     EvidenceCondition.PROMISE_WINDOW)


def parse_reply(text: str) -> dict | None:
    """The asked JSON object, or None: a reply that is not one must not be guessed at."""
    match = _JSON_RE.search(text or "")
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def trace_key(condition: str, company: str | None, year: int | None, text: str | None) -> tuple:
    """How a trace written at retrieval time is found again at classification time."""
    return (condition, company or "", year, normalise(text or ""))


@dataclass(slots=True)
class Trace:
    condition: str
    company: str
    year: int | None
    target: str
    hops: int = 0                 # planner calls made
    input_tokens: int = 0
    output_tokens: int = 0
    planner_ms: float = 0.0
    stop: str = ""
    steps: list[dict] = field(default_factory=list)
    final: list[str] = field(default_factory=list)   # how each span handed over was found


class AgenticRetriever:
    def __init__(self, build_id: str = DEFAULT_BUILD, client: LLMClient | None = None, corpus=None,
                 reranker=None) -> None:
        raw_hops = os.getenv("AGENTIC_MAX_HOPS", "").strip()
        self.max_hops = int(raw_hops) if raw_hops else None
        self.timeout_s = float(os.getenv("AGENTIC_TIMEOUT_S", "") or 90)
        self.select = os.getenv("AGENTIC_SELECT", "").strip() or "verified"
        if self.select not in ("verified", "rerank", "neighbours"):
            raise ValueError("AGENTIC_SELECT must be verified, rerank or neighbours")
        self.client = client or LLMClient()   # one client: the harness reads its embedding usage
        self.corpus = corpus or corpus_tools.load("statements", build_id=build_id, client=self.client)
        self.reranker = reranker or CrossEncoderReranker()
        self.prompts = {name: sections(PROMPT_DIR / file) for name, file in PROMPTS.items()}
        self.traces: dict[tuple, Trace] = {}
        self.finished: dict[str, list[Trace]] = {}
        self._lock = threading.Lock()
        self.trace_file: Path = TRACE_DIR / f"traces-{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}.jsonl"

    def describe(self) -> dict[str, object]:
        info = dict(self.corpus.describe()) if hasattr(self.corpus, "describe") else {}
        shas = {name: hashlib.sha256((PROMPT_DIR / file).read_bytes()).hexdigest()[:12]
                for name, file in PROMPTS.items()}
        return {**info, "max_hops": self.max_hops, "timeout_s": self.timeout_s, "select": self.select,
                "prompts": shas, "trace_file": self.trace_file.name}

    # ------------------------------------------------------------------ planner
    def hops_for(self, default: int) -> int:
        return default if self.max_hops is None else self.max_hops

    def ask(self, prompt: str, user: str, trace: Trace) -> dict | None:
        """One planner call, charged to the trace. None, with the reason as the stop, ends the loop."""
        parts = self.prompts[prompt]
        messages = [{"role": "system", "content": parts["system"]}, {"role": "user", "content": user}]
        trace.hops += 1
        for max_tokens in (PLAN_TOKENS, 2 * PLAN_TOKENS):
            try:
                reply = self.client.chat(messages, max_tokens=max_tokens,
                                         response_format={"type": "json_object"})
            except Exception as exc:  # noqa: BLE001 - a failed planner call ends the loop, not the run
                trace.stop = "llm_error"
                trace.steps.append({"error": str(exc)[:200]})
                return None
            trace.input_tokens += reply.input_tokens
            trace.output_tokens += reply.output_tokens
            trace.planner_ms += reply.latency_ms
            obj = parse_reply(reply.text)
            if obj is not None:
                return obj
        trace.stop = "parse_error"
        return None

    # ------------------------------------------------------------------ protocol
    def retrieve(self, query: Query, *, k: int = 3) -> list[EvidenceSpan]:
        if query.condition not in _AGENT_CONDITIONS:
            return self._plain(query, k)     # the in-system fixed arms: the baseline's own search
        from agentic_rag import rq1, rq2

        policy = rq2 if query.condition is EvidenceCondition.PROMISE_WINDOW else rq1
        if self.hops_for(policy.DEFAULT_HOPS) == 0 and policy is rq1:
            return self._plain(query, k, why="agent:hop0")
        trace = Trace(condition=query.condition.value, company=query.company or "", year=query.anchor_year,
                      target=query.target_text or query.text)
        started = time.perf_counter()
        spans = policy.run(self, query, k, trace, started)
        trace.final = [s.why for s in spans]
        trace.planner_ms = round(trace.planner_ms, 1)
        key = trace_key(trace.condition, query.company, query.anchor_year, query.target_text)
        with self._lock:
            self.traces[key] = trace
            self.finished.setdefault(trace.condition, []).append(trace)
            self.trace_file.parent.mkdir(parents=True, exist_ok=True)
            with self.trace_file.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(asdict(trace), ensure_ascii=False) + "\n")
        return spans

    def _plain(self, query: Query, k: int, why: str | None = None) -> list[EvidenceSpan]:
        cross_year = query.condition.value.startswith("cross_year")
        text = f"{query.aspect}. {query.text}" if query.aspect else query.text
        spans = self.corpus.search(text, company=query.company, year_from=query.year_from,
                                   year_to=query.year_to,
                                   exclude_year=query.anchor_year if cross_year else None,
                                   k=k, mode="hybrid+rerank")
        return [s.model_copy(update={"why": why}) for s in spans] if why else spans

    # ------------------------------------------------------------------ what the run reports
    def stats(self, condition: str) -> dict | None:
        traces = self.finished.get(condition)
        if not traces:
            return None
        n = len(traces)
        spans = [why for t in traces for why in t.final]
        later = sum(not why.startswith("agent:hop0") for why in spans)
        return {
            "items": n,
            "planner_calls_per_item": sum(t.hops for t in traces) / n,
            "input_tokens_per_item": sum(t.input_tokens for t in traces) / n,
            "output_tokens_per_item": sum(t.output_tokens for t in traces) / n,
            "planner_ms_per_item": sum(t.planner_ms for t in traces) / n,
            "later_hop_share": later / len(spans) if spans else 0.0,
            "no_evidence_share": sum(not t.final for t in traces) / n,
            "stop": dict(Counter(t.stop for t in traces).most_common()),
            "by_found": dict(Counter(spans).most_common()),
        }
