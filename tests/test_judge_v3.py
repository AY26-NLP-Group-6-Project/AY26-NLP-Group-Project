"""Judge v3's labels and rule, and judging over an earlier run's evidence: no network."""

import json
from types import SimpleNamespace

from gw_common.judges import promise as J

PROMISE = {
    "promise_id": "P1",
    "company": "Acme",
    "metric": "water intensity",
    "quantity": 1.5,
    "unit": "m3/m2",
    "direction": "achieve",
    "baseline_year": None,
    "target_year": 2023,
    "recurring": False,
    "origin": {"year": 2021, "page": 3, "text": "We target 1.50 m3/m2 by FY2023."},
}
ALL = J.V3_FEATURES
NONE = frozenset()


def row(ref="E1", year=2023, relation="this_target", result="none", change="none", figure=None):
    return {
        "ref": ref,
        "year": year,
        "relation": relation,
        "deadline_result": result,
        "change": change,
        "figure": figure,
    }


def test_with_no_features_it_reads_labels_as_v2_does():
    cases = [
        [row(result="met")],
        [row(result="missed")],
        [row(result="met"), row("E2", result="missed")],
        [row(change="later")],
        [row(relation="same_metric")],
        [row(relation="other")],
        [row(year=2022, result="missed")],
    ]
    for labels in cases:
        assert J.decide_v3(labels, False, PROMISE, None, NONE)[:2] == J.decide(labels, False, 2023)
    assert J.decide_v3([row(relation="proxy", result="met")], False, PROMISE, None, NONE)[0] == "unclear"
    assert J.decide_v3([row(result="partial")], False, PROMISE, None, NONE)[0] == "unclear"


def test_proxy_settles_only_with_its_feature_and_is_recorded():
    labels = [row(relation="proxy", result="met")]
    assert J.decide_v3(labels, False, PROMISE, None, frozenset({"proxy"})) == ("achieved", ["E1"], ["proxy"])
    both = labels + [row("E2", result="met")]
    assert J.decide_v3(both, False, PROMISE, None, ALL)[2] == []  # the commitment's own words say so too


def test_partial_is_a_miss_from_the_deadline_on():
    assert J.decide_v3([row(result="partial")], False, PROMISE, None, ALL) == ("failed", ["E1"], ["partial"])
    assert J.decide_v3([row(year=2022, result="partial")], False, PROMISE, None, ALL)[0] == "disappeared"
    assert (
        J.decide_v3([row(result="partial"), row("E2", result="met")], False, PROMISE, None, ALL)[0]
        == "unclear"
    )


def test_figure_needs_the_same_unit_a_level_and_a_direction():
    f = {"value": 2.78, "unit": "m3 / m2"}
    assert J.figure_result(f, PROMISE, "lower") == "missed"
    assert J.figure_result({"value": 1.2, "unit": "m3/m2"}, PROMISE, "lower") == "met"
    assert J.figure_result({"value": 2.78, "unit": "%"}, PROMISE, "lower") == "none"
    assert J.figure_result(f, PROMISE, None) == "none"
    assert J.figure_result(f, {**PROMISE, "direction": "reduce"}, "lower") == "none"
    assert J.figure_result(f, {**PROMISE, "quantity": None}, "lower") == "none"
    assert J.figure_result({"value": "n/a", "unit": "m3/m2"}, PROMISE, "lower") == "none"


def test_figure_speaks_where_the_words_do_not_and_not_before_the_deadline():
    f = {"value": 2.78, "unit": "m3/m2"}
    labels = [row(relation="same_metric", figure=f)]
    assert J.decide_v3(labels, False, PROMISE, "lower", ALL) == ("failed", ["E1"], ["figure"])
    assert J.decide_v3(labels, False, PROMISE, "lower", NONE)[0] == "unclear"
    assert (
        J.decide_v3([row(year=2022, relation="same_metric", figure=f)], False, PROMISE, "lower", ALL)[0]
        == "disappeared"
    )
    assert (
        J.decide_v3([row(relation="this_target", result="met", figure=f)], False, PROMISE, "lower", ALL)[0]
        == "achieved"
    )


def test_parse_keeps_results_on_the_right_relations_and_flags_gaps():
    evidence = [{"ref": "E1", "year": 2023}, {"ref": "E2", "year": 2023}, {"ref": "E3", "year": 2023}]
    obj = {
        "annual": False,
        "evidence": [
            {
                "ref": "E1",
                "relation": "proxy",
                "deadline_result": "met",
                "change": "later",
                "figure": {"value": 1, "unit": "x"},
            },
            {
                "ref": "E2",
                "relation": "same_metric",
                "deadline_result": "met",
                "change": "later",
                "figure": {"value": 2, "unit": "x"},
            },
            {"ref": "E3", "relation": "other", "deadline_result": "met", "figure": {"value": 3, "unit": "x"}},
        ],
    }
    labels, complete = J.parse_labels_v3(obj, evidence)
    assert complete
    assert labels[0]["deadline_result"] == "met" and labels[0]["change"] == "none"
    assert labels[1]["deadline_result"] == "none" and labels[1]["figure"]["value"] == 2
    assert labels[2]["figure"] is None
    assert J.parse_labels_v3({"evidence": []}, evidence)[1] is False


def test_v3_shows_more_of_each_statement_and_a_garbled_reply_settles_nothing(monkeypatch):
    seen = []

    def chat(messages, max_tokens=0, response_format=None):
        seen.append(messages[1]["content"])
        return SimpleNamespace(text="not json")

    evidence = [{"ref": "E1", "year": 2023, "page": 1, "text": "x" * 900}]
    prompt = J.sections(J.PROMPTS["v3"])
    out = J.propose_v3(PROMISE, evidence, SimpleNamespace(chat=chat), prompt)
    assert out["outcome"] == "unclear" and out["parse_ok"] is False and len(seen) == 2
    assert "x" * 900 in seen[0]
    monkeypatch.setenv("GW_JUDGE_CHARS", "500")
    monkeypatch.setenv("GW_JUDGE_V3_FEATURES", "proxy")
    assert J.describe("v3")["evidence_chars"] == 500 and J.describe("v3")["features"] == ["proxy"]


def test_a_v3_reply_reaches_the_outcome():
    reply = {
        "annual": False,
        "better": "lower",
        "outcome": "unclear",
        "rationale": "r",
        "evidence": [
            {
                "ref": "E1",
                "relation": "same_metric",
                "deadline_result": "none",
                "change": "none",
                "figure": {"value": 2.78, "unit": "m3/m2"},
            }
        ],
    }
    client = SimpleNamespace(
        chat=lambda messages, max_tokens=0, response_format=None: SimpleNamespace(text=json.dumps(reply))
    )
    evidence = [{"ref": "E1", "year": 2023, "page": 1, "text": "Intensity was 2.78 m3/m2 in FY2023."}]
    out = J.propose_v3(PROMISE, evidence, client, J.sections(J.PROMPTS["v3"]))
    assert (out["outcome"], out["basis"], out["model_outcome"]) == ("failed", ["figure"], "unclear")


def test_the_filter_keeps_hop_zero_and_only_the_added_statements_the_labels_used(tmp_path):
    from agentic_rag.analyze_judge import write_verified

    judged, source = tmp_path / "judged", tmp_path / "source"
    judged.mkdir()
    source.mkdir()

    def span(i, why):
        return {
            "statement_id": f"r2023p0001s00{i}",
            "text": f"statement {i}",
            "company": "Acme",
            "year": 2023,
            "page": 1,
            "file": "f",
            "score": 0.0,
            "why": why,
        }

    spans = [
        span(1, "agent:hop0:retrieved"),
        span(2, "agent:probe"),
        span(3, "agent:hop1:search"),
        span(4, "agent:hop1:around"),
    ]
    (source / "evidence.jsonl").write_text(
        json.dumps({"condition": "promise_window", "item_id": "P1", "spans": spans}) + "\n", encoding="utf-8"
    )
    labels = [
        row("E1"),
        row("E2", relation="same_metric", result="none"),
        row("E3", result="met"),
        row("E4", relation="other"),
    ]
    rep = {"item_id": "P1", "rep": 0, "labels": labels}
    (judged / "predictions.jsonl").write_text(json.dumps(rep) + "\n", encoding="utf-8")
    out = tmp_path / "out" / "evidence.jsonl"
    assert write_verified(judged, source, out) == (1, 2)
    kept = json.loads(out.read_text(encoding="utf-8"))["spans"]
    assert [s["why"] for s in kept] == ["agent:hop0:retrieved", "agent:hop1:search"]
