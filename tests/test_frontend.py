"""The demo front end's core helpers: the dev split, systems per task, the steps with a fake system,
custom queries, pages and the published-run table. No Streamlit, no network."""

import random
import sys
from pathlib import Path

import pytest
from gw_common.eval import rq2 as R
from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvalItem, EvidenceCondition, EvidenceSpan, GoldItem, Label, Prediction

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "frontend"))
import core  # noqa: E402


class FakeRetriever:
    def retrieve(self, query, *, k=10):
        # the first span is the target sentence itself: the harness must drop it
        target = EvidenceSpan(
            statement_id="t",
            text=query.target_text or "",
            company=query.company or "",
            year=query.anchor_year or 0,
            page=1,
            why="fake",
        )
        spans = [
            EvidenceSpan(
                statement_id=f"s{i}",
                text=f"statement {i} about {query.aspect}",
                company=query.company or "",
                year=2024,
                page=i,
                why="fake",
            )
            for i in range(1, 6)
        ]
        return [target, *spans][:k]


class FakeClassifier:
    def classify(self, items, *, condition, evidence=None):
        return [
            Prediction(
                item_id=it.item_id,
                label=Label.PLANNING,
                evidence_ids=[s.statement_id for s in (evidence or {}).get(it.item_id, [])],
                rationale="fake",
                input_tokens=10,
                output_tokens=2,
                llm_calls=1,
            )
            for it in items
        ]


class FakeSystem(BaseSystem):
    name = "fake"

    def __init__(self):
        self._retriever = FakeRetriever()

    def supported_conditions(self):
        return [EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.CROSS_YEAR_RRF]

    def retriever(self):
        return self._retriever

    def classifier(self):
        return FakeClassifier()


def _gold(i: int, split: str = "dev") -> GoldItem:
    return GoldItem(
        item_id=str(i),
        text=f"We will reduce waste by 2025 ({i}).",
        aspect="waste",
        company="Acme",
        year=2023,
        page=i,
        gold_label=Label.PLANNING,
        label_source="human_majority",
        split=split,
    )


def test_tasks_and_definitions():
    assert set(core.TASKS) == {core.RQ1, core.RQ2}
    for task in core.TASKS.values():
        assert task["definition"].strip() and task["labels"] and task["k"] > 0


def test_systems_for_each_task_uses_the_registry():
    rq1, _ = core.systems_for(core.RQ1)
    assert "majority" in rq1 and rq1["majority"] == ["sentence_only"]
    assert "promise_window" not in sum(rq1.values(), [])
    rq2, _ = core.systems_for(core.RQ2)
    assert "majority" not in rq2
    assert all(conds == ["promise_window"] for conds in rq2.values())


def test_pick_and_find_avoid_the_current_item():
    items = [_gold(i) for i in range(1, 6)]
    rng = random.Random(0)
    for _ in range(20):
        assert core.item_id(core.RQ1, core.pick(items, core.RQ1, "3", rng)) != "3"
    assert core.find(items, core.RQ1, " 4 ").item_id == "4"
    assert core.find(items, core.RQ1, "99") is None
    assert core.companies(items, core.RQ1) == ["Acme"]
    assert core.gold_of(core.RQ1, items[0]) == "planning"
    assert core.gold_of(core.RQ1, items[0].to_eval_item()) is None


def test_rq1_steps_with_a_fake_system():
    system, item = FakeSystem(), _gold(1)
    assert core.retrieve_rq1(system, item, EvidenceCondition.SENTENCE_ONLY, 3) == ([], 0)
    spans, dropped = core.retrieve_rq1(system, item, EvidenceCondition.CROSS_YEAR_RRF, 3)
    assert len(spans) == 2 and dropped == 1  # the target sentence was returned and dropped
    spans, dropped = core.retrieve_rq1(system, item, EvidenceCondition.CROSS_YEAR_RRF, 6)
    assert len(spans) == 5 and dropped == 1
    pred = core.classify_rq1(system, item, EvidenceCondition.CROSS_YEAR_RRF, spans)
    assert pred.label is Label.PLANNING and pred.evidence_ids == [s.statement_id for s in spans]
    assert core.vote_rq1([pred, pred, Prediction(item_id="1", label=Label.NONE)]) is Label.PLANNING
    custom = core.custom_rq1("  We installed solar panels. ", "", "Acme", 2024)
    assert (
        isinstance(custom, EvalItem) and custom.aspect is None and custom.text == "We installed solar panels."
    )
    assert core.classify_rq1(system, custom, EvidenceCondition.SENTENCE_ONLY, []).item_id == "custom"


def test_custom_promise_is_a_valid_promise_window_query():
    promise = core.custom_promise(
        "Acme", " We aim for zero incidents by 2024. ", "zero incidents", 2022, 2024, True
    )
    query = R.promise_query(promise)
    assert query.condition is EvidenceCondition.PROMISE_WINDOW
    assert (query.year_from, query.year_to) == core.window_of(promise) == (2023, 2025)
    assert (
        query.meta["promise"]["recurring"] is True
        and query.target_text == "We aim for zero incidents by 2024."
    )
    assert core.gold_of(core.RQ2, promise) is None
    assert core.vote_rq2(["achieved", "revised", "revised"]) == "failed"
    assert core.vote_rq2(["achieved", "failed", "unclear"]) == "unclear"


def test_usage_delta_and_pages(tmp_path):
    assert core.usage_delta({"calls": 3, "input_tokens": 50}, {"calls": 1, "input_tokens": 20}) == {
        "calls": 2,
        "cache_hits": 0,
        "input_tokens": 30,
        "output_tokens": 0,
        "embed_tokens": 0,
    }
    assert core.resolve_pdf(None) is None
    assert core.resolve_pdf("raw/nowhere/2024_00000000.pdf") is None
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "r.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "hello")
    doc.save(pdf)
    assert core.page_png(pdf, 1, zoom=0.5).startswith(b"\x89PNG")
    assert core.page_png(pdf, 2) is None


def test_published_runs_read_the_results_folder():
    for task in (core.RQ1, core.RQ2):
        rows = core.published_runs(task)
        if not rows:  # a checkout without published runs
            continue
        assert {"run", "system", "condition", "vote macro-F1", "store"} <= set(rows[0])
        assert all(r["condition"] == "promise_window" for r in rows) == (task == core.RQ2)
