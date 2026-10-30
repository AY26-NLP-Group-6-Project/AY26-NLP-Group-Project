"""The RQ2 gold file: the group's sheet, rounds for the model annotators, assembly and the split."""

import json

import pytest
from graph_rag.promises import gold as G

openpyxl = pytest.importorskip("openpyxl")


def _promise(pid, company, year=2022, deadline=2023):
    return {
        "promise_id": pid,
        "company": company,
        "metric": "incidents",
        "quantity": 0.0,
        "unit": "cases",
        "direction": "maintain",
        "baseline_year": None,
        "target_year": deadline,
        "kind": "quantitative",
        "recurring": True,
        "checkable": True,
        "related": [],
        "stated_in_years": [year],
        "origin": {"year": year, "page": 3, "text": f"We aim for zero incidents in FY{deadline}."},
    }


def _outcome(pid, outcome):
    return {
        "promise_id": pid,
        "outcome": outcome,
        "rationale": "r",
        "evidence_refs": ["E1"],
        "evidence": [{"ref": "E1", "year": 2023, "page": 4, "text": "There were no incidents in FY2023."}],
    }


def _write(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


IDS = [f"P{i:03d}" for i in range(1, 13)]


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "out_dir", lambda cfg: tmp_path)
    _write(
        tmp_path / "promises.jsonl", [_promise(i, "Acme" if n % 2 else "Other") for n, i in enumerate(IDS)]
    )
    outcomes = tmp_path / "outcomes.jsonl"
    _write(outcomes, [_outcome(i, "achieved") for i in IDS])
    # the group's sheet, under its own sheet name, two header rows, six rows labelled by both annotators
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SampledAnnotation-RQ2"
    ws.append(["Promise"] + [None] * 12)
    ws.append(
        [
            "promise_id",
            "company",
            "stated_in",
            "promise_sentence",
            "extracted",
            "restated_in",
            "other_versions",
            "evidence",
            "a1_outcome",
            "a1_note",
            "a2_outcome",
            "a2_note",
            "final",
        ]
    )
    labels = [
        ("achieved", "achieved", "achieved"),
        ("Failed", "unclear", "unclear"),
        ("unclear", "unclear", "unclear"),
        ("achieved", "achieved", "achieved"),
        ("disappeared", "disappeared", "disappeared"),
        ("failed", "failed", "failed"),
    ]
    for pid, (a1, a2, final) in zip(IDS, labels, strict=False):
        ws.append(
            [
                pid,
                "Acme",
                "2022 report, p.3",
                "text",
                "metric",
                None,
                None,
                "[E1] ...",
                a1,
                "E1",
                a2,
                "E1 too",
                final,
            ]
        )
    ws.append(
        [
            IDS[6],
            "Acme",
            "2022 report, p.3",
            "text",
            "metric",
            None,
            None,
            "[E1] ...",
            None,
            None,
            None,
            None,
            None,
        ]
    )  # not labelled
    sheet = tmp_path / "group.xlsx"
    wb.save(sheet)
    return tmp_path, outcomes, sheet


def test_group_sheet_is_read_whatever_its_sheet_name(world):
    _, _, sheet = world
    rows = G.human_rows(sheet)
    assert [r["promise_id"] for r in rows] == IDS[:6]
    assert rows[1]["a1_outcome"] == "failed" and rows[1]["final"] == "unclear"  # case folded
    assert len(G.read_group_sheet(sheet)) == 7


def test_packets_render_and_brief(world):
    tmp_path, outcomes, _ = world
    cells = G.packets(None, outcomes)
    assert set(cells) == set(IDS) and cells["P001"]["deadline"] == 2023
    text = G.render(
        cells["P001"],
        {
            "final": "achieved",
            "a1_outcome": "achieved",
            "a1_note": "E1",
            "a2_outcome": "unclear",
            "a2_note": "no verdict",
        },
    )
    assert (
        "2023 report (deadline year)" in text and "final outcome: achieved" in text and "no verdict" in text
    )
    brief = G.brief()
    assert all(label in brief for label in G.LABELS) and "Boundaries the group settled" in brief
    assert "adjudicate" not in brief.split("## Output")[0].lower().replace("adjudicated", "")


def test_stratified_floor_and_reference_choice(world):
    _, _, sheet = world
    rows = G.human_rows(sheet)
    by_class = {}
    for r in rows:
        by_class.setdefault(r["final"], []).append(r["promise_id"])
    picked = G.stratified(by_class, 4, seed=1, floor=1)
    assert len(picked) == 4 and len(set(picked)) == 4
    refs = G.choose_references(rows, exclude={"P001"}, per_class=1, seed=1)
    assert "P001" not in {r["promise_id"] for r in refs}
    assert any(r["promise_id"] == "P002" for r in refs)  # the disagreement is the unclear example


def test_round_labels_adjudication_and_scoring(world):
    tmp_path, outcomes, sheet = world
    cells = G.packets(None, outcomes)
    rows = G.human_rows(sheet)
    index = G.write_round(tmp_path / "rounds", "calibration", IDS[:4], cells, rows[4:], batch_size=2)
    assert len(index["batches"]) == 2 and (tmp_path / "rounds/calibration/references.md").exists()
    labels_dir = tmp_path / "rounds/calibration/labels"
    for batch in index["batches"]:
        for a, outcome in (("a1", "achieved"), ("a2", "unclear")):
            (labels_dir / f"{batch['batch']}.{a}.jsonl").write_text(
                "\n".join(
                    json.dumps(
                        {"promise_id": i, "outcome": outcome if i != "P003" else "unclear", "note": "E1"}
                    )
                    for i in batch["ids"]
                ),
                encoding="utf-8",
            )
    labels = G.collect(labels_dir)
    assert len(labels["a1"]) == 4 and labels["a2"]["P001"]["outcome"] == "unclear"
    report = G.against_human(labels, rows[:4])
    assert report["a1"]["n"] == 4 and report["a1"]["accuracy"] == pytest.approx(3 / 4)  # P002 human unclear
    assert report["a1_vs_a2"]["accuracy"] == pytest.approx(1 / 4)  # only P003 agrees
    assert {d["promise_id"] for d in report["disagreements"]} == {"P001", "P002", "P004"}
    adj = G.write_adjudication(tmp_path / "rounds", "calibration", cells, labels, batch_size=5)
    assert adj["ids"] == ["P001", "P002", "P004"]
    assert "annotator a2: **unclear**" in (
        tmp_path / "rounds/calibration/adjudication/batches/01.md"
    ).read_text(encoding="utf-8")


def test_assemble_split_and_snapshot(world):
    tmp_path, outcomes, sheet = world
    human = G.human_rows(sheet)
    model = {"a1": {}, "a2": {}}
    for i in IDS[6:]:
        model["a1"][i] = {"outcome": "achieved", "note": "E1"}
        model["a2"][i] = {"outcome": "achieved" if i != "P010" else "failed", "note": "E1"}
    with pytest.raises(ValueError):
        G.assemble(human, model, {}, pilot=set())
    items = G.assemble(
        human, model, {"P010": {"outcome": "failed", "note": "deadline passed"}}, pilot={"P001", "P007"}
    )
    assert len(items) == 12
    by_id = {i["promise_id"]: i for i in items}
    assert by_id["P010"]["outcome"] == "failed" and by_id["P010"]["adjudicate"] == "deadline passed"
    assert by_id["P001"]["split"] == "dev" and by_id["P007"]["split"] == "dev"  # pilot pinned
    assert sum(i["split"] == "dev" for i in items) == round(G.DEV_SHARE * 12)
    assert {i["label_source"] for i in items} == {"human_pair", "model_pair"}
    report = G.write_snapshot(items, tmp_path / "promises.jsonl", tmp_path / "eval")
    path = tmp_path / "eval" / report["snapshot"]
    assert path.exists() and report["items"] == 12 and report["splits"]["dev"] == round(G.DEV_SHARE * 12)
    first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert {"promise_id", "outcome", "split", "label_source", "company", "deadline"} <= set(first)
    assert (tmp_path / "eval" / f"{G.DATASET}.build_report.json").exists()
