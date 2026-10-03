"""RQ2 plumbing: target validation, merging restatements into promises, checkability, sheet scoring."""

import json

import pytest
from graph_rag.promises import build as B
from graph_rag.promises import extract as E
from graph_rag.promises import sheet as S

STATEMENT = "We aim to reduce Scope 1 emissions by 15% by 2025 from a 2019 baseline."


def raw(**over):
    base = {"target_text": "reduce Scope 1 emissions by 15% by 2025", "metric": "Scope 1 emissions",
            "category": "emissions control", "direction": "reduce", "quantity": 15, "unit": "%",
            "baseline_year": 2019, "target_year": 2025, "kind": "quantitative", "recurring": False}
    return {**base, **over}


def test_candidate_needs_a_cue_and_a_year_not_before_the_report():
    assert E.is_candidate(STATEMENT, 2021)
    assert not E.is_candidate(STATEMENT, 2026)                       # the only year is already past
    assert not E.is_candidate("Emissions were 15% lower in 2025 than in the base year.", 2025)  # no cue
    assert not E.is_candidate("We aim high by 2030.", 2021)          # too short to be a statement


def test_validate_keeps_verbatim_targets_and_names_the_reason_otherwise():
    target, why = E.validate(raw(), STATEMENT, 2021)
    assert why == "ok" and target["target_year"] == 2025 and target["quantity"] == 15.0
    assert E.validate(raw(target_text="cut Scope 1 by 15%"), STATEMENT, 2021)[1] == "span_not_in_statement"
    assert E.validate(raw(target_year=2020), STATEMENT, 2021)[1] == "target_year_out_of_range"
    assert E.validate(raw(target_year="soon"), STATEMENT, 2021)[1] == "no_target_year"
    assert E.validate(raw(metric=" "), STATEMENT, 2021)[1] == "no_metric"
    loose, _ = E.validate(raw(category="climate", kind="vague", quantity="15"), STATEMENT, 2021)
    assert loose["category"] is None and loose["kind"] == "qualitative" and loose["quantity"] is None


def target(tid, company, year, metric, target_year, quantity=15.0, recurring=False):
    return {"target_id": tid, "stmt_id": tid, "company": company, "year": year, "page": 3, "file": "sha",
            "text": STATEMENT, "target_text": "reduce Scope 1 emissions by 15% by 2025", "metric": metric,
            "category": "emissions control", "kind": "quantitative", "direction": "reduce",
            "quantity": quantity, "unit": "%", "baseline_year": 2019, "target_year": target_year,
            "recurring": recurring}


def test_restatements_merge_and_moved_goalposts_are_linked_not_merged():
    targets = [
        target("a", "Acme", 2021, "Scope 1 emissions", 2025),
        target("b", "Acme", 2022, "Scope 1 GHG emissions", 2025),          # restated a year later
        target("c", "Acme", 2023, "Scope 1 emissions", 2030, quantity=42.0),  # a different goal
        target("d", "Acme", 2022, "Scope 1 emissions", 2025, quantity=None),  # number dropped: same promise
        target("e", "Other", 2021, "Scope 1 emissions", 2025),             # another company
    ]
    promises = B.consolidate(targets)
    acme = [p for p in promises if p["company"] == "Acme"]
    assert len(promises) == 3 and len(acme) == 2
    first = next(p for p in acme if p["target_year"] == 2025)
    assert first["origin"]["year"] == 2021 and first["stated_in_years"] == [2021, 2022]
    assert len(first["restatements"]) == 2 and first["quantity"] == 15.0
    assert [r["target_year"] for r in first["related"]] == [2030]         # the moved goalpost


def test_checkable_rules():
    promises = B.consolidate([
        target("a", "Acme", 2021, "Scope 1 emissions", 2025),
        target("b", "Acme", 2025, "water intensity", 2025),               # stated in its deadline year
        target("c", "Acme", 2021, "energy use", 2030),                    # deadline after the corpus
        target("d", "Gone", 2021, "waste diverted", 2023),                # no report for the deadline year
        target("e", "Acme", 2021, "this target", 2024),                   # bare anaphor
    ])
    B.mark_checkable(promises, {"Acme": {2021, 2024, 2025}, "Gone": {2021}}, last_year=2025)
    by_metric = {p["metric"]: p for p in promises}
    scope1 = by_metric["Scope 1 emissions"]
    assert scope1["checkable"] and scope1["outcome_years"] == [2025]
    assert by_metric["water intensity"]["not_checkable_because"] == ["stated_in_or_after_deadline_year"]
    assert by_metric["energy use"]["not_checkable_because"] == ["deadline_after_corpus"]
    assert by_metric["waste diverted"]["not_checkable_because"] == ["no_report_for_deadline_year"]
    assert by_metric["this target"]["not_checkable_because"] == ["vague_metric"]


def test_sample_covers_rare_classes_and_caps_companies():
    promises = [{"promise_id": f"P{i}", "company": f"C{i % 3}"} for i in range(60)]
    outcomes = {p["promise_id"]: {"outcome": "failed" if i < 4 else "achieved"}
                for i, p in enumerate(promises)}
    chosen = S.sample(promises, outcomes, n=12, seed=1)
    assert len(chosen) == 12
    # every member of the rare class makes it in
    assert sum(outcomes[p["promise_id"]]["outcome"] == "failed" for p in chosen) == 4
    counts = {}
    for p in chosen:
        counts[p["company"]] = counts.get(p["company"], 0) + 1
    assert max(counts.values()) <= S.PER_COMPANY
    assert [p["promise_id"] for p in S.sample(promises, outcomes, 12, 1)] == [p["promise_id"] for p in chosen]


def test_score_reads_a_filled_sheet(tmp_path, monkeypatch):
    from openpyxl import Workbook

    monkeypatch.setattr(S, "out_dir", lambda cfg: tmp_path)
    promises = [{"promise_id": f"P{i}", "kind": "quantitative"} for i in range(1, 5)]
    (tmp_path / "promises.jsonl").write_text("\n".join(json.dumps(p) for p in promises), encoding="utf-8")
    key = {"P1": {"outcome": "achieved"}, "P2": {"outcome": "achieved"}, "P3": {"outcome": "failed"},
           "P4": {"outcome": "unclear"}}
    (tmp_path / "promise_sheet_key.json").write_text(json.dumps(key), encoding="utf-8")
    wb = Workbook()
    ws = wb.active
    ws.title = S.SHEET_NAME
    ws.append(S.COLUMNS)
    blank = [None] * 7
    ws.append(["P1", *blank, "Y", "Y", "achieved", "E1", None])
    ws.append(["P2", *blank, "Y", "N", "failed", "E2", None])
    ws.append(["P3", *blank, "Y", "Y", "failed", "E1", None])
    ws.append(["P4", *blank, "N", None, None, None, "a result, not a commitment"])
    path = tmp_path / "check.xlsx"
    wb.save(path)

    result = S.score(None, path)
    assert result["judged"] == 4 and result["extraction"]["promise_precision"] == 0.75
    assert result["extraction"]["fields_ok_rate"] == pytest.approx(2 / 3)
    assert result["outcome"]["n"] == 3 and result["outcome"]["accuracy"] == pytest.approx(2 / 3)
    assert result["outcome"]["human_distribution"] == {"achieved": 1, "failed": 2}
    assert result["outcome"]["per_class"]["failed"] == {"precision": 1.0, "recall": 0.5, "support": 2}
    assert S.cohen_kappa(["a", "a", "b", "b"], ["a", "b", "b", "b"]) == pytest.approx(0.5)
