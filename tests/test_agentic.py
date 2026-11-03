"""Behaviour of the agentic retriever's loop with a scripted planner: no network, no passage store."""

import json
from collections import defaultdict

import pytest
from agentic_rag import AgentCostClassifier
from agentic_rag import agent as A
from baseline_rag.chunks import Chunk
from baseline_rag.index import BM25
from baseline_rag.retrieve import HybridRetriever
from gw_common.llm import ChatResult
from gw_common.schemas import EvalItem, EvidenceCondition, Label, Prediction, Query

TARGET = "We will meet this target through the programme described above."
CHUNKS = [
    Chunk("c0", TARGET, "Acme", 2024, 3, "acme/2024.pdf", []),
    Chunk("c1", "The programme described above targets Scope 2 emissions.", "Acme", 2023, 4,
          "acme/2023.pdf", []),
    Chunk("c2", "Solar panels on warehouse rooftops supply renewable electricity.", "Acme", 2023, 7,
          "acme/2023.pdf", []),
    Chunk("c3", "Green Power Programme: rooftop solar across all warehouses by 2026.", "Acme", 2025, 2,
          "acme/2025.pdf", []),
    Chunk("c4", "Green Power Programme rooftop solar at Other's sites.", "Other", 2025, 2, "o/2025.pdf", []),
]


class FakeStore:
    _allowed = HybridRetriever._allowed
    allowed_ids = HybridRetriever.allowed_ids

    def __init__(self, build_id, mode, client=None):
        self.chunks = CHUNKS
        self.bm25 = BM25([c.indexed_text() for c in CHUNKS])
        self._by_company = defaultdict(list)
        for i, c in enumerate(CHUNKS):
            self._by_company[c.company].append(i)


class ScriptedClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, messages, **kw):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(text=reply, model="fake", input_tokens=100, output_tokens=20, latency_ms=5.0)


@pytest.fixture
def make(monkeypatch, tmp_path):
    monkeypatch.setattr(A, "HybridRetriever", FakeStore)
    monkeypatch.setattr(A, "TRACE_FILE", tmp_path / "traces.jsonl")
    monkeypatch.setenv("AGENTIC_BASE_MODE", "bm25")

    def _make(replies, max_hops=2):
        monkeypatch.setenv("AGENTIC_MAX_HOPS", str(max_hops))
        return A.AgenticRetriever(client=ScriptedClient(replies))
    return _make


def query(condition=EvidenceCondition.CROSS_YEAR_AGENTIC):
    return Query(text=TARGET, company="Acme", aspect="renewable energy", anchor_year=2024,
                 target_text=TARGET, condition=condition)


def plan(sufficient, queries=(), years="any"):
    return json.dumps({"sufficient": sufficient, "need": "x", "queries": list(queries), "years": years})


def test_parse_plan_reads_json_and_stops_on_garbage():
    p = A.parse_plan('Sure: {"sufficient": false, "queries": ["green power"], "years": "later"}')
    assert (p.sufficient, p.queries, p.years, p.parse_ok) == (False, ["green power"], "later", True)
    assert A.parse_plan("no json here") == A.Plan(sufficient=True, queries=[], parse_ok=False)
    assert A.parse_plan('{"sufficient": false, "years": "sideways"}').years == "any"


def test_non_agentic_conditions_make_no_llm_call(make):
    r = make([])
    spans = r.retrieve(query(EvidenceCondition.CROSS_YEAR_RRF), k=3)
    assert spans and all(s.why == "agent:hop0" for s in spans)
    assert r.client.calls == [] and r.traces == {}


def test_sufficient_stops_after_one_planner_call(make):
    r = make([plan(True)])
    r.retrieve(query(), k=3)
    (trace,) = r.traces.values()
    assert (trace.hops, trace.stop, trace.input_tokens, trace.output_tokens) == (1, "sufficient", 100, 20)


def test_rewrite_finds_new_evidence_and_respects_filters(make):
    r = make([plan(False, ["Green Power Programme rooftop solar"], years="later"), plan(True)])
    spans = r.retrieve(query(), k=3)
    by_id = {s.statement_id: s for s in spans}
    plain = make([]).retrieve(query(EvidenceCondition.CROSS_YEAR_RRF), k=3)
    assert plain[0].statement_id != "c3" and spans[0].statement_id == "c3"   # the rewrite promoted it
    assert "c0" not in by_id               # the target's own report year is excluded in cross-year
    assert "c4" not in by_id               # never another company
    (trace,) = r.traces.values()
    assert (trace.hops, trace.stop) == (2, "sufficient")


def test_hop_cap_and_repeated_queries(make):
    r = make([plan(False, ["solar"]), plan(False, ["solar"])], max_hops=2)
    r.retrieve(query(), k=3)
    (trace,) = r.traces.values()
    assert (trace.hops, trace.stop) == (2, "no_new_query")
    r = make([plan(False, ["solar"]), plan(False, ["scope 2"])], max_hops=2)
    r.retrieve(query(), k=3)
    assert next(iter(r.traces.values())).stop == "max_hops"


def test_zero_hops_is_plain_search(make):
    r = make([], max_hops=0)
    plain = [s.statement_id for s in make([]).retrieve(query(EvidenceCondition.CROSS_YEAR_RRF), k=3)]
    assert [s.statement_id for s in r.retrieve(query(), k=3)] == plain
    assert next(iter(r.traces.values())).hops == 0


def test_planner_failure_ends_loop_not_run(make):
    r = make([RuntimeError("gateway timeout")])
    assert r.retrieve(query(), k=3)
    assert next(iter(r.traces.values())).stop == "llm_error"


def test_agent_cost_is_charged_to_agentic_predictions_only(make):
    r = make([plan(True)])
    r.retrieve(query(), k=3)

    class Inner:
        def describe(self):
            return {"style": "cited"}

        def classify(self, items, *, condition, evidence=None):
            return [Prediction(item_id=it.item_id, label=Label.PLANNING, input_tokens=10, output_tokens=5,
                               llm_calls=1) for it in items]

    clf = AgentCostClassifier(Inner(), r)
    item = EvalItem(item_id="1", text=TARGET, company="Acme", year=2024)
    (p,) = clf.classify([item], condition=EvidenceCondition.CROSS_YEAR_AGENTIC)
    assert (p.input_tokens, p.output_tokens, p.graph_hops, p.llm_calls) == (110, 25, 1, 1)
    (p,) = clf.classify([item], condition=EvidenceCondition.CROSS_YEAR_RRF)
    assert (p.input_tokens, p.graph_hops) == (10, 0)
    assert clf.describe()["agent"]["max_hops"] == 2
