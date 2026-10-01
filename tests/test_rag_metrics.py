"""RAGAS-style metrics: the arithmetic is hand-checked, the judge is faked."""

import csv
import json

import numpy as np
import pytest
from gw_common.eval import rag_metrics as R
from gw_common.llm import ChatResult, LLMSettings
from gw_common.schemas import GoldItem, Label

ITEM = GoldItem(item_id="1", text="We will install solar panels by 2026.", aspect="solar panels",
                company="Acme", year=2024, page=12, context_prev="Energy is our largest footprint.",
                context_next="Work starts next quarter.", gold_label=Label.PLANNING, label_source="test")
SPANS = [{"company": "Acme", "year": 2023, "page": 8, "text": "We study rooftop solar."},
         {"company": "Acme", "year": 2025, "page": 30, "text": "Revenue grew by 4 per cent."}]


def test_context_precision_is_rank_weighted():
    assert R.context_precision([True, False, True]) == pytest.approx((1 / 1 + 2 / 3) / 2)
    assert R.context_precision([False, True]) == pytest.approx(0.5)
    assert R.context_precision([False, False]) == 0.0
    assert R.context_precision([]) is None


def test_sources_match_what_the_classifier_saw():
    tags = [t for t, _ in R.sources_for(ITEM, "sentence_only", [])]
    assert tags == ["T"]
    assert [t for t, _ in R.sources_for(ITEM, "local", [])] == ["T", "C"]
    shown = R.sources_for(ITEM, "cross_year_rrf", SPANS)
    assert [t for t, _ in shown] == ["T", "E1", "E2"] and shown[1][1].startswith("(Acme, 2023, p.8)")


class _FakeClient:
    """Answers each judge prompt by its section, and embeds deterministically."""

    settings = LLMSettings(chat_model="fake-judge")

    def chat(self, messages, **_):
        system = messages[0]["content"]
        if "atomic statements" in system:
            reply = {"statements": [{"statement": "A plan is dated 2026.", "supported": True, "source": "T"},
                                    {"statement": "Panels are already installed.", "supported": False,
                                     "source": "none"}]}
        elif "most likely questions" in system:
            reply = {"questions": ["q1", "q2", "q3"], "noncommittal": False}
        else:
            reply = {"verdicts": [{"ref": "E1", "relevant": True, "reason": "same aspect"},
                                  {"ref": "E2", "relevant": False, "reason": "about revenue"}]}
        return ChatResult(text=json.dumps(reply), model="fake-judge")

    def embed(self, texts):
        # the original question is [1, 0]; generated questions sit at 60 degrees to it
        out = [[1.0, 0.0]] + [[0.5, np.sqrt(0.75)]] * (len(texts) - 1)
        return np.asarray(out, dtype=np.float32)


def test_score_one_hand_computed():
    judge = R.RagJudge(client=_FakeClient(), workers=1)
    pred = {"label": "planning", "rationale": "A dated plan; panels installed.",
            "citations": [{"ref": "T"}, {"ref": "E1"}]}
    row = judge.score_one(ITEM, "cross_year_rrf", pred, SPANS)
    assert row["faithfulness"] == 0.5 and len(row["statements"]) == 2
    assert row["answer_relevance"] == pytest.approx(0.5)
    assert row["context_relevance"] == 0.5 and row["context_precision"] == 1.0
    assert row["correct"] is True and row["cited"] == ["T", "E1"]
    # nothing retrieved: context metrics are undefined, not zero
    row = judge.score_one(ITEM, "sentence_only", pred, [])
    assert row["context_precision"] is None and row["context_relevance"] is None
    # no rationale (label-only classifier): nothing to judge
    row = judge.score_one(ITEM, "sentence_only", {"label": "planning", "rationale": ""}, [])
    assert row["faithfulness"] is None and row["answer_relevance"] is None


def test_summary_and_blind_check_round_trip(tmp_path, monkeypatch):
    judge = R.RagJudge(client=_FakeClient(), workers=1)
    pred = {"condition": "cross_year_rrf", "rep": 0, "item_id": "1", "label": "planning",
            "rationale": "A dated plan; panels installed.", "citations": []}
    (tmp_path / "predictions.jsonl").write_text(json.dumps(pred) + "\n", encoding="utf-8")
    (tmp_path / "evidence.jsonl").write_text(
        json.dumps({"condition": "cross_year_rrf", "item_id": "1", "spans": SPANS}) + "\n", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"run_id": "r", "dataset_id": "gw1000", "label_source": "test"}), encoding="utf-8")
    monkeypatch.setattr(R.datasets, "load", lambda *_: ([ITEM], "hash"))

    summary = R.score_run(tmp_path, judge=judge)
    block = summary["conditions"]["cross_year_rrf"]
    assert block["faithfulness"] == 0.5 and block["context_precision"] == 1.0
    assert block["when_correct"]["n"] == 1 and block["when_wrong"]["n"] == 0
    assert (tmp_path / "ragas.md").exists() and "faithfulness" in (tmp_path / "ragas.md").read_text("utf-8")

    sheet = tmp_path / "check.csv"
    info = R.export_check(tmp_path, sheet, n_answers=5)
    assert info["rows"] == 4 and info["by_kind"] == {"statement_supported": 2, "passage_relevant": 2}
    with sheet.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert all(r["human_verdict"] == "" for r in rows)             # blind: no judge verdict in the sheet
    assert "supported" not in ",".join(rows[0].keys())
    key = json.loads((tmp_path / "ragas_check_key.json").read_text("utf-8"))
    for r in rows:                                                   # a human who agrees with the judge
        r["human_verdict"] = "Y" if key[r["check_id"]] else "N"
    with sheet.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    result = R.score_check(tmp_path, sheet)
    assert result["statement_supported"]["agreement"] == 1.0
    assert result["statement_supported"]["cohen_kappa"] == 1.0


def test_cohen_kappa_hand_computed():
    assert R.cohen_kappa([True, True, False, False], [True, False, False, False]) == pytest.approx(0.5)
    assert R.cohen_kappa([], []) is None
