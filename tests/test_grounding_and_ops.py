"""Cited classifier output, citation resolution, and the speed / cost / grounding blocks."""

import pytest
from gw_common.classifiers.llm_action import LLMActionClassifier, parse_cited, resolve_citations
from gw_common.eval import ops
from gw_common.llm import ChatResult, LLMSettings
from gw_common.schemas import Citation, EvalItem, EvidenceCondition, EvidenceSpan, Label, Prediction

ITEM = EvalItem(item_id="1", text="We will install solar panels by 2026.", aspect="solar panels",
                company="Acme", year=2024, page=12, file="raw/acme/2024.pdf",
                context_prev="Energy is our largest footprint.", context_next="Work starts next quarter.")
SPANS = [EvidenceSpan(statement_id="s1", text="Solar panels were installed at two sites.", company="Acme",
                      year=2025, page=30, file="sha25"),
         EvidenceSpan(statement_id="s2", text="We study rooftop solar.", company="Acme", year=2023, page=8)]


def test_parse_cited_reads_json_and_falls_back():
    label, why, refs, ok = parse_cited(
        'Sure: {"label": "planning", "rationale": "A dated commitment.", "evidence": ["T", "E1"]}')
    assert (label, why, refs, ok) == (Label.PLANNING, "A dated commitment.", ["T", "E1"], True)
    label, why, refs, ok = parse_cited("I think this is implemented.")
    assert (label, why, refs, ok) == (Label.IMPLEMENTED, "", [], False)
    assert parse_cited('{"label": "done"}')[3] is False          # not a label: not a valid reply


def test_citations_resolve_to_sources_and_bad_refs_are_counted():
    cites, invalid = resolve_citations(["T", "[E1]", "e2", "E9", "C", "foo", "T"], ITEM, SPANS,
                                       has_context=False)
    assert [c.ref for c in cites] == ["T", "E1", "E2"]
    assert invalid == 3                                           # E9 not shown, C not given, foo unknown
    target, first = cites[0], cites[1]
    assert (target.company, target.year, target.page, target.file) == ("Acme", 2024, 12, "raw/acme/2024.pdf")
    assert (first.statement_id, first.year, first.page, first.file) == ("s1", 2025, 30, "sha25")
    assert first.quote.startswith("Solar panels were installed")
    cites, invalid = resolve_citations(["C"], ITEM, [], has_context=True)
    assert cites[0].ref == "C" and "Energy is our largest footprint" in cites[0].quote and invalid == 0


class _FakeClient:
    def __init__(self, reply):
        self.reply, self.messages = reply, None

    def chat(self, messages, **_):
        self.messages = messages
        return ChatResult(text=self.reply, model="fake", input_tokens=100, output_tokens=20, latency_ms=50.0)


def test_cited_classifier_tags_sources_and_returns_rationale():
    client = _FakeClient('{"label": "planning", "rationale": "Dated plan.", "evidence": ["T", "E2"]}')
    clf = LLMActionClassifier(client=client, workers=1, style="cited")
    pred = clf.classify([ITEM], condition=EvidenceCondition.CROSS_YEAR_RRF, evidence={"1": SPANS})[0]
    user = client.messages[1]["content"]
    assert "[T] TARGET sentence" in user and "[E1] (Acme, 2025, p.30)" in user and "[E2]" in user
    assert pred.label is Label.PLANNING and pred.rationale == "Dated plan." and pred.parse_ok
    assert [c.ref for c in pred.citations] == ["T", "E2"] and pred.citations[1].statement_id == "s2"
    assert pred.evidence_ids == ["s1", "s2"]


def test_label_style_keeps_the_v1_prompt():
    client = _FakeClient("implemented")
    clf = LLMActionClassifier(client=client, workers=1, style="label")
    pred = clf.classify([ITEM], condition=EvidenceCondition.SENTENCE_ONLY)[0]
    assert pred.label is Label.IMPLEMENTED and pred.rationale == "" and pred.citations == []
    assert "[T]" not in client.messages[1]["content"]
    assert clf.describe()["style"] == "label" and len(clf.describe()["prompt_sha256"]) == 12
    with pytest.raises(ValueError):
        LLMActionClassifier(client=client, style="essay")


def _pred(i, latency, cites=(), rationale="why", calls=1):
    return Prediction(item_id=str(i), label=Label.PLANNING, latency_ms=latency, input_tokens=400,
                      output_tokens=50, llm_calls=calls, rationale=rationale,
                      citations=[Citation(ref=r) for r in cites])


def test_speed_and_cost_hand_computed():
    preds = [_pred(1, 1000.0), _pred(2, 3000.0)]
    settings = LLMSettings(price_in=1.0, price_out=4.0, price_embed=0.02)
    out = ops.speed_and_cost(preds, wall_s=4.0, retrieval_ms={"1": 100.0, "2": 300.0},
                             settings=settings, embed_tokens=1000)
    assert out["items_per_s"] == 0.5 and out["mean_ms"] == 2000.0
    assert out["end_to_end"]["mean_ms"] == 2200.0
    assert out["input_tokens_per_item"] == 400 and out["cached_calls"] == 0
    # (800 * 1 + 100 * 4 + 1000 * 0.02) / 1e6
    assert out["cost_usd"] == pytest.approx(0.00122)
    assert out["cost_per_1k_items_usd"] == pytest.approx(0.61)
    # no prices configured: tokens are still reported, dollars are not invented
    assert ops.speed_and_cost(preds, 4.0, settings=LLMSettings())["cost_usd"] is None
    assert ops.speed_and_cost([_pred(1, 0.1, calls=0)], 0.01)["cached_calls"] == 1
    speed = ops.retrieval_speed({"1": 100.0, "2": 300.0})
    assert speed["total_s"] == pytest.approx(0.4) and speed["queries_per_s"] == pytest.approx(5.0)


def test_grounding_counts_evidence_use():
    preds = [_pred(1, 1.0, cites=("T", "E1")), _pred(2, 1.0, cites=("T",)), _pred(3, 1.0, rationale="")]
    evidence = {"1": SPANS, "2": SPANS}                    # item 3 had no evidence
    g = ops.grounding(preds, evidence)
    assert g["rationale_rate"] == pytest.approx(2 / 3)
    assert g["cites_target_rate"] == pytest.approx(2 / 3)
    assert g["items_with_evidence"] == 2 and g["evidence_use_rate"] == 0.5
    assert g["evidence_spans_cited_share"] == pytest.approx(1 / 4)
    assert ops.mean_of([{"a": {"b": 1.0}}, {"a": {"b": 3.0}}, {"a": {}}], "a", "b") == 2.0


def test_a_reply_the_gateway_will_not_finish_is_a_failed_parse_not_a_dead_run():
    from gw_common.llm import OutputBudgetExceeded

    class _Refusing:
        def chat(self, messages, **_):
            raise OutputBudgetExceeded("max_tokens or model output limit was reached")

    clf = LLMActionClassifier(client=_Refusing(), workers=1, style="cited")
    pred = clf.classify([ITEM], condition=EvidenceCondition.CROSS_YEAR_RRF, evidence={"1": SPANS})[0]
    assert pred.parse_ok is False and pred.label is Label.INDETERMINATE
    assert pred.evidence_ids == ["s1", "s2"] and "output budget" in pred.rationale
