"""Behaviour of the agentic retriever with a scripted planner: no network, no store."""

import json

import pytest
from agentic_rag import AgentCostClassifier
from agentic_rag import agent as A
from agentic_rag import rq1 as Q1
from agentic_rag import rq2 as Q2
from agentic_rag.tools import Fence
from baseline_rag.index import BM25
from gw_common.corpus import Report
from gw_common.eval.rq2 import promise_query
from gw_common.llm import ChatResult
from gw_common.schemas import EvalItem, EvidenceCondition, EvidenceSpan, Label, Prediction, Query

TARGET = "We will meet this target through the programme described above."
ROWS = [
    ("c0", TARGET, "Acme", 2024, 3),
    ("c1", "The Green Power Programme targets Scope 2 emissions across warehouses.", "Acme", 2024, 3),
    ("c2", "The programme described above targets Scope 2 emissions.", "Acme", 2023, 4),
    ("c3", "Solar panels on warehouse rooftops supply renewable electricity.", "Acme", 2023, 7),
    ("c4", "Green Power Programme: rooftop solar across all warehouses by 2026.", "Acme", 2025, 2),
    ("c5", "Green Power Programme rooftop solar at Other's sites.", "Other", 2025, 2),
]


class FakeCorpus:
    def __init__(self, rows=ROWS):
        self.spans = [EvidenceSpan(statement_id=i, text=t, company=c, year=y, page=p, file=f"{c}/{y}")
                      for i, t, c, y, p in rows]
        self.bm25 = BM25([s.text for s in self.spans])
        self.searches = []

    def search(self, text, *, company=None, year_from=None, year_to=None, exclude_year=None, k=10,
               mode="hybrid"):
        self.searches.append({"text": text, "mode": mode})
        keep = {i for i, s in enumerate(self.spans) if s.company == company and s.year != exclude_year
                and (year_from is None or s.year >= year_from) and (year_to is None or s.year <= year_to)}
        ranked = self.bm25.search(text, keep, k)
        return [self.spans[i].model_copy(update={"why": mode}) for i, _ in ranked]

    def get(self, statement_id):
        return next((s for s in self.spans if s.statement_id == statement_id), None)

    def page(self, company, year, page):
        return [s for s in self.spans if (s.company, s.year, s.page) == (company, year, page)]

    def neighbours(self, statement_id, *, before=1, after=1):
        s = self.get(statement_id)
        on_page = self.page(s.company, s.year, s.page)
        at = on_page.index(s)
        return on_page[max(0, at - before):at + after + 1]

    def reports(self, company):
        years = sorted({s.year for s in self.spans if s.company == company})
        return [Report(company=company, year=y, file=f"{company}/{y}", pages=9, statements=1) for y in years]

    def companies(self):
        return sorted({s.company for s in self.spans})


class ScriptedClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, messages, **kw):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(text=reply, model="fake", input_tokens=100, output_tokens=20, latency_ms=5.0)


class WordReranker:
    """More shared words, higher score."""

    def rerank(self, query, documents):
        words = set(query.lower().split())
        return [float(len(words & set(d.lower().split()))) for d in documents]


@pytest.fixture
def make(monkeypatch, tmp_path):
    monkeypatch.setattr(A, "TRACE_DIR", tmp_path)
    monkeypatch.delenv("AGENTIC_SELECT", raising=False)

    def _make(replies, hops=None, select=None, rows=ROWS):
        if hops is None:
            monkeypatch.delenv("AGENTIC_MAX_HOPS", raising=False)
        else:
            monkeypatch.setenv("AGENTIC_MAX_HOPS", str(hops))
        if select:
            monkeypatch.setenv("AGENTIC_SELECT", select)
        return A.AgenticRetriever(client=ScriptedClient(replies), corpus=FakeCorpus(rows),
                                  reranker=WordReranker())
    return _make


def query(condition=EvidenceCondition.COMPANY_AGENTIC):
    any_year = condition.value != "same_report_rrf"
    year = None if any_year else 2024
    return Query(text=TARGET, company="Acme", aspect="renewable energy", anchor_year=2024, target_text=TARGET,
                 condition=condition, year_from=year, year_to=year, meta={"page": 3})


def gate(*questions, queries=("Green Power Programme",)):
    gaps = [{"kind": "reference", "phrase": "this target", "question": q} for q in questions]
    return json.dumps({"gaps": gaps, "queries": list(queries)})


def verify(answers, resolved=True, queries=()):
    return json.dumps({"answers": list(answers), "resolved": resolved, "queries": list(queries)})


NO_GAP = json.dumps({"gaps": [], "queries": []})
ONE_GAP = "Which programme and target does this refer to?"


def test_parse_reply_reads_json_and_refuses_garbage():
    assert A.parse_reply('Sure: {"gaps": []}') == {"gaps": []}
    assert A.parse_reply("no json here") is None and A.parse_reply("[1]") is None


# ------------------------------------------------------------------ the fence
def test_fence_keeps_company_years_and_target():
    corpus = FakeCorpus()
    fence = Fence(corpus, query(EvidenceCondition.CROSS_YEAR_AGENTIC))
    assert fence.years() == [2023, 2025]
    assert {s.statement_id for s in fence.search("programme target Green Power")} <= {"c2", "c3", "c4"}
    assert fence.search("programme", year=2024) == [] and fence.around_target() == []
    whole = Fence(corpus, query())
    assert [s.statement_id for s in whole.around_target()] == ["c1"]   # never the target itself
    assert all(s.statement_id != "c0" for s in whole.search(TARGET, k=6))
    assert fence.page(2024, 3) == []


# ------------------------------------------------------------------ RQ1
def test_fixed_arms_are_one_reranked_search_with_no_llm(make):
    r = make([])
    spans = r.retrieve(query(EvidenceCondition.CROSS_YEAR_RRF), k=3)
    assert spans and r.client.calls == [] and r.traces == {}
    assert r.corpus.searches == [{"text": f"renewable energy. {TARGET}", "mode": "hybrid+rerank"}]


def test_no_gap_gives_no_evidence_and_no_search(make):
    r = make([NO_GAP])
    assert r.retrieve(query(), k=3) == []
    (trace,) = r.traces.values()
    assert (trace.hops, trace.stop, trace.input_tokens, trace.output_tokens) == (1, "no_gap", 100, 20)
    assert r.corpus.searches == []
    assert r.stats("company_agentic")["no_evidence_share"] == 1.0


def test_verified_selection_keeps_only_what_answers(make):
    r = make([gate(ONE_GAP), verify(["P1"])])
    spans = r.retrieve(query(), k=3)
    assert len(spans) == 1 and spans[0].why == "agent:hop1"
    (trace,) = r.traces.values()
    assert (trace.hops, trace.stop) == (2, "resolved")


def test_verifier_naming_nothing_gives_no_evidence(make):
    r = make([gate(ONE_GAP), verify([], resolved=False)])
    assert r.retrieve(query(), k=3) == []
    assert next(iter(r.traces.values())).stop == "unresolved"


def test_rerank_selection_ignores_the_verifier_and_ranks_against_the_question(make):
    r = make([gate(ONE_GAP), verify([], resolved=False)], select="rerank")
    spans = r.retrieve(query(), k=2)
    assert len(spans) == 2 and "c0" not in {s.statement_id for s in spans}


def test_neighbours_selection_keeps_the_next_sentence_whatever_the_verifier_says(make):
    r = make([gate(ONE_GAP), verify([], resolved=False)], select="neighbours")
    assert [s.statement_id for s in r.retrieve(query(), k=3)] == ["c1"]
    r = make([gate(ONE_GAP), verify([], resolved=False)], select="neighbours")
    assert r.retrieve(query(EvidenceCondition.CROSS_YEAR_AGENTIC), k=3) == []    # its report is out of reach


def test_a_third_hop_searches_again_and_finds_new_evidence(make):
    r = make([gate(ONE_GAP, queries=("warehouse solar",)), verify([], False, ["Green Power Programme 2026"]),
              verify(["P1"])], hops=3)
    spans = r.retrieve(query(), k=3)
    (trace,) = r.traces.values()
    assert trace.hops == 3 and spans and spans[0].why in ("agent:hop1", "agent:hop2")


def test_one_hop_is_gate_and_rerank_without_a_verifier(make):
    r = make([gate(ONE_GAP)], hops=1)
    assert r.retrieve(query(), k=3) and len(r.client.calls) == 1


def test_zero_hops_is_the_plain_search(make):
    r = make([], hops=0)
    plain = [s.statement_id for s in make([]).retrieve(query(EvidenceCondition.CROSS_YEAR_RRF), k=3)]
    got = r.retrieve(query(EvidenceCondition.CROSS_YEAR_AGENTIC), k=3)
    assert [s.statement_id for s in got] == plain and {s.why for s in got} == {"agent:hop0"}
    assert r.client.calls == []


def test_planner_failure_falls_back_to_the_sentence_alone(make):
    r = make([RuntimeError("gateway timeout")])
    assert r.retrieve(query(), k=3) == []
    assert next(iter(r.traces.values())).stop == "llm_error"
    r = make(["garbage", "still garbage"])
    assert r.retrieve(query(), k=3) == []
    (trace,) = r.traces.values()
    assert trace.stop == "parse_error" and trace.input_tokens == 200    # both attempts are charged


def test_agent_cost_is_charged_to_agentic_predictions_only(make):
    r = make([NO_GAP])
    r.retrieve(query(), k=3)

    class Inner:
        def describe(self):
            return {"style": "cited"}

        def classify(self, items, *, condition, evidence=None):
            return [Prediction(item_id=it.item_id, label=Label.PLANNING, input_tokens=10, output_tokens=5,
                               llm_calls=1) for it in items]

    clf = AgentCostClassifier(Inner(), r)
    item = EvalItem(item_id="1", text=TARGET, company="Acme", year=2024)
    (p,) = clf.classify([item], condition=EvidenceCondition.COMPANY_AGENTIC)
    assert (p.input_tokens, p.output_tokens, p.graph_hops, p.llm_calls) == (110, 25, 1, 1)
    (p,) = clf.classify([item], condition=EvidenceCondition.CROSS_YEAR_AGENTIC)   # another arm's trace
    assert (p.input_tokens, p.graph_hops) == (10, 0)
    (p,) = clf.classify([item], condition=EvidenceCondition.CROSS_YEAR_RRF)
    assert (p.input_tokens, p.graph_hops) == (10, 0)
    assert clf.describe()["agent"]["prompts"]["rq1_gate"]


# ------------------------------------------------------------------ RQ2
PROMISE_ROWS = [
    ("o1", "We aim for zero accidents in FY2023.", "Acme", 2022, 5),
    ("a1", "Lost time accidents were reviewed by the safety committee.", "Acme", 2023, 8),
    ("a2", "Target for accidents: zero lost time accidents in FY2023.", "Acme", 2023, 9),
    ("a3", "We recorded two lost time accidents, requires improvement.", "Acme", 2023, 9),
    ("a4", "Our zero accidents target has been postponed to FY2026.", "Acme", 2024, 3),
    ("x1", "Zero accidents target was achieved at Other.", "Other", 2023, 9),
]
PROMISE = {
    "promise_id": "P1", "company": "Acme", "metric": "accidents", "quantity": 0.0, "unit": " cases",
    "direction": "reach", "baseline_year": None, "target_year": 2023, "recurring": False, "related": [],
    "origin": {"year": 2022, "page": 5, "text": PROMISE_ROWS[0][1],
               "target_text": "zero accidents in FY2023"},
}


def plan(*actions, stop=False):
    return json.dumps({"result_seen": None, "change_seen": None, "missing": "x", "actions": list(actions),
                       "stop": stop})


def test_zero_hops_is_budget_and_neighbours_inside_the_window(make):
    r = make([], hops=0, rows=PROMISE_ROWS)
    spans = r.retrieve(promise_query(PROMISE), k=20)
    ids = {s.statement_id for s in spans}
    assert r.client.calls == [] and "o1" not in ids and "x1" not in ids     # the window, the company
    assert {"a1", "a2", "a3", "a4"} <= ids
    assert all(s.why.startswith("agent:hop0") for s in spans)
    assert r.stats("promise_window")["later_hop_share"] == 0.0


def test_planner_reads_the_promise_and_never_the_gold(make):
    r = make([plan(stop=True)], rows=PROMISE_ROWS)
    r.retrieve(promise_query({**PROMISE, "a1_note": "SECRET"}), k=20)
    user = r.client.calls[0][1]["content"]
    assert "deadline year 2023" in user and "Reports in the window: 2023, 2024" in user
    assert "SECRET" not in user and "Evidence gathered so far" in user


def test_a_change_is_looked_for_before_the_first_planner_call(make):
    r = make([plan(stop=True)], rows=PROMISE_ROWS)
    r.retrieve(promise_query(PROMISE), k=20)
    probes = [c for c in r.corpus.searches if c["mode"] == "bm25"]
    assert len(probes) == 1 and "postponed" in probes[0]["text"]
    assert next(iter(r.traces.values())).stop == "planner_stop"


def test_actions_are_fenced_and_a_search_outside_the_window_brings_nothing(make):
    rows = PROMISE_ROWS
    r = make([plan({"tool": "search", "query": "something else", "year": 2021, "mode": "keyword"},
                   {"tool": "around", "ref": "E99"}, {"tool": "fly"})], rows=rows)
    r.retrieve(promise_query(PROMISE), k=20)
    (trace,) = r.traces.values()
    assert trace.steps[0]["brought"] == [0, 0, 0] and trace.stop == "nothing_new"


def test_later_hops_keep_their_slots_under_the_cap():
    pool = Q2.Pool()
    mk = lambda i, y=2023: EvidenceSpan(statement_id=f"s{i}", text=f"statement {i}", company="A", year=y)  # noqa: E731
    pool.add([mk(i) for i in range(20)], "agent:hop0:retrieved")
    pool.add([mk(i) for i in range(20, 30)], "agent:hop1:search")
    final = pool.final(20)
    assert len(final) == 20
    assert sum(s.why.startswith("agent:hop1") for s in final) == Q2.AGENT_SLOTS
    pool = Q2.Pool()
    pool.add([mk(i) for i in range(3)], "agent:hop0:retrieved")
    pool.add([mk(i) for i in range(3, 13)], "agent:hop1:search")
    assert len(pool.final(20)) == 13                 # room left over is used


def test_rq1_helpers_cap_and_dedupe():
    assert Q1.queries_of({"queries": ["A b", "a B", "c", "d"]}, ["c"]) == ["A b", "d"]
    assert Q1.gaps_of({"gaps": [{"question": "q"}, {"no": 1}, "x"]}) == [{"question": "q"}]
    assert Q1.gaps_of({"gaps": "none"}) == []
