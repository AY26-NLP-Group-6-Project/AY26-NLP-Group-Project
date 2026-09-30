"""The eval workbook reader: what it accepts, what it refuses, and that agreement is recomputed."""

import pytest
from gw_common import annotation
from gw_common.schemas import Label
from openpyxl import Workbook

HEAD = ["id", "text", "aspect", "label", "category", "split", "row_type", "aspect_source", "aspect_weak",
        "company", "sgx_code", "year", "page", "file", "context_prev", "context_next", "pilot",
        "A1", "A2", "A3", "A4", "A5", "A6", "n_annotators", "agreement", "adjudicated",
        "llm_pre_claude", "llm_pre_deepseek", "llm_pre_gpt", "notes"]


def _row(i, text, label, split="dev", humans=("",) * 6, aspect="water use"):
    return [i, text, aspect, label, "resource optimisation", split, "aspect", "llm_proposed", "",
            "Acme", "AC1", 2024, 3, "raw/acme/2024.pdf", "before", "after", "",
            *humans, sum(bool(h) for h in humans), 1.0, "", label, label, "none", ""]


def _book(tmp_path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "eval"
    ws.append(HEAD)
    for r in rows:
        ws.append(r)
    path = tmp_path / "eval.xlsx"
    wb.save(path)
    return path


def test_build_reads_eval_sheet(tmp_path, monkeypatch):
    monkeypatch.setattr(annotation, "EVAL_DIR", tmp_path)
    monkeypatch.setattr("gw_common.datasets.EVAL_DIR", tmp_path)
    six = ("implemented",) * 5 + ("planning",)
    path = _book(tmp_path, [_row(1, "We cut water use by ten per cent.", "implemented", humans=six),
                            _row(2, "We plan to cut water use next year.", "planning", split="test")])
    report = annotation.build(path)
    assert report["items"] == 2 and report["splits"] == {"dev": 1, "test": 1}
    assert report["rows_by_annotator_count"] == {6: 1, 0: 1}
    assert report["agreement"]["fleiss_all"]["n_rows"] == 1
    assert report["llm_pre_vs_human"] == {"claude": 1.0, "deepseek": 1.0, "gpt": 0.0}
    from gw_common import datasets

    items, _ = datasets.load("gw1000", "human_majority")
    assert [i.gold_label for i in items] == [Label.IMPLEMENTED, Label.PLANNING]
    assert "notes" not in items[0].meta and items[0].context_prev == "before"


def test_build_refuses_duplicates_and_bad_values(tmp_path, monkeypatch):
    monkeypatch.setattr(annotation, "EVAL_DIR", tmp_path)
    monkeypatch.setattr("gw_common.datasets.EVAL_DIR", tmp_path)
    same = "We cut water use by ten per cent."
    with pytest.raises(ValueError, match="duplicate"):
        annotation.build(_book(tmp_path, [_row(1, same, "implemented"), _row(2, same, "planning")]))
    with pytest.raises(ValueError, match="label"):
        annotation.build(_book(tmp_path, [_row(1, same, "done")]))
    with pytest.raises(ValueError, match="split"):
        annotation.build(_book(tmp_path, [_row(1, same, "planning", split="train")]))
