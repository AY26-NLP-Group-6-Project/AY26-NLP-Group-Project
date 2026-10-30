"""The two-annotator sheet: export with a prefilled first annotator, blind copy, merge, scoring."""

import json
from pathlib import Path

import pytest
from graph_rag.promises import pair_sheet as P
from graph_rag.promises import sheet as S
from openpyxl import Workbook, load_workbook

openpyxl = pytest.importorskip("openpyxl")


def _promise(pid, company, year=2022, deadline=2023):
    return {"promise_id": pid, "company": company, "metric": "incidents", "quantity": 0.0, "unit": "cases",
            "direction": "maintain", "baseline_year": None, "target_year": deadline, "kind": "quantitative",
            "recurring": True, "checkable": True, "related": [], "stated_in_years": [year],
            "origin": {"year": year, "page": 3, "text": f"We aim for zero incidents in FY{deadline}."}}


def _outcome(pid, outcome):
    return {"promise_id": pid, "outcome": outcome, "rationale": "r", "evidence_refs": ["E1"],
            "evidence": [{"ref": "E1", "year": 2023, "page": 4,
                          "text": "There were no incidents in FY2023."}]}


def _write(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "out_dir", lambda cfg: tmp_path)
    monkeypatch.setattr(P, "out_dir", lambda cfg: tmp_path)
    ids = [f"P{i:03d}" for i in range(1, 9)]
    _write(tmp_path / "promises.jsonl",
           [_promise(i, "Acme" if n % 2 else "Other") for n, i in enumerate(ids)])
    outcomes = tmp_path / "outcomes.jsonl"
    labels = ["achieved", "revised", "unclear", "failed"]
    _write(outcomes, [_outcome(i, labels[n % 4]) for n, i in enumerate(ids)])
    # an earlier single-annotator sheet on three of them, with its key and strata
    wb = Workbook()
    ws = wb.active
    ws.title = S.SHEET_NAME
    ws.append(S.COLUMNS)
    blank = [None] * 7
    ws.append(["P001", *blank, "Y", "Y", "achieved", "E1", None])
    ws.append(["P002", *blank, "Y", "N", "revised", "E1", "re-dated"])
    ws.append(["P003", *blank, "N", None, None, None, "a result, not a commitment"])
    held = tmp_path / "earlier.xlsx"
    wb.save(held)
    held.with_suffix(".key.json").write_text(json.dumps({
        "P001": {"outcome": "achieved"}, "P002": {"outcome": "revised"}, "P003": {"outcome": "unclear"},
        S.POOL: {"achieved": 2, "revised": 2, "unclear": 2, "failed": 2}}), encoding="utf-8")
    return tmp_path, outcomes, held


def test_export_prefills_annotator1_mixes_in_random_rows_and_hides_them_in_the_copy(world):
    tmp_path, outcomes, held = world
    out = tmp_path / "pair.xlsx"
    info = P.export_pair(None, out, outcomes, held_out=held, n_random=3, seed=1)
    assert info["rows"] == 6 and info["held_out"] == 3 and info["random"] == 3 and info["random_pool"] == 5
    first_three = [r["promise_id"] for r in P.read_pair_rows(out)][:3]
    assert first_three == ["P001", "P002", "P003"]                   # the rows judged before come first
    rows = {r["promise_id"]: r for r in P.read_pair_rows(out)}
    assert rows["P002"]["a1_outcome"] == "failed"                   # revised became failed
    assert rows["P002"]["a1_note"] == "re-dated"
    assert rows["P003"]["a1_outcome"] == "not_a_promise"                                    # promise_ok N
    assert all(rows[i]["a1_outcome"] is None for i in rows if i not in ("P001", "P002", "P003"))
    key = json.loads(out.with_suffix(".key.json").read_text(encoding="utf-8"))
    assert key["P002"]["reported"] == "failed" and key["P002"]["part"] == "held_out"
    assert sum(v["part"] == "random" for k, v in key.items() if k != P.DESIGN) == 3
    wb = load_workbook(out)
    assert wb.sheetnames == [P.SHEET_NAME, P.GUIDE_SHEET]
    assert [c.value for c in wb[P.SHEET_NAME][2]] == P.HEADER
    assert len(P.HEADER) == 14
    guide_cells = [c.value for row in wb[P.GUIDE_SHEET].iter_rows() for c in row if c.value]
    assert any(str(v).startswith("=SUMPRODUCT") for v in guide_cells)
    assert "promise_ok" not in guide_cells and "evidence_ref" not in guide_cells

    copy = P.blind_copy(out, tmp_path / "copy.xlsx", annotator=2)
    copied = {r["promise_id"]: r for r in P.read_pair_rows(copy)}
    assert copied["P001"]["a1_outcome"] is None and copied["P001"]["evidence"] == rows["P001"]["evidence"]


def test_merge_then_score_reports_agreement_and_the_two_pools(world):
    tmp_path, outcomes, held = world
    out = tmp_path / "pair.xlsx"
    P.export_pair(None, out, outcomes, held_out=held, n_random=3, seed=1)
    copy = P.blind_copy(out, tmp_path / "copy.xlsx", annotator=2)
    wb = load_workbook(copy)
    ws = wb[P.SHEET_NAME]
    for row in ws.iter_rows(min_row=P.FIRST_ROW):
        pid = row[0].value
        row[P.COL["a2_outcome"] - 1].value = {"P003": "not_a_promise", "P001": "unclear"}.get(pid, "failed")
        row[P.COL["a2_note"] - 1].value = "E1"
    wb.save(copy)
    assert P.merge(out, copy, annotator=2)["copied"] == 6

    wb = load_workbook(out)
    ws = wb[P.SHEET_NAME]
    for row in ws.iter_rows(min_row=P.FIRST_ROW):            # the first annotator finishes, then adjudication
        pid = row[0].value
        if row[P.COL["a1_outcome"] - 1].value is None:
            row[P.COL["a1_outcome"] - 1].value = "failed"
        row[P.COL["final"] - 1].value = {"P001": "achieved", "P003": "not_a_promise"}.get(pid, "failed")
    wb.save(out)

    result = P.score_pair(None, out)
    assert result["filled"] == {"annotator1": 6, "annotator2": 6, "final": 6}
    iaa = result["iaa"]
    assert iaa["n"] == 6 and iaa["accuracy"] == pytest.approx(5 / 6)     # only P001 differs
    assert result["system_vs_final"]["n"] == 6
    assert result["population_random"]["n"] == 3 and result["population_random"]["pool"] == 5
    assert result["population_held_out"]["pool"] == 6        # strata with no sampled row are left out
    assert Path(out.with_suffix(".result.json")).exists()
