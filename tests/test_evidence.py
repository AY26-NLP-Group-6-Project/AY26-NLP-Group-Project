import json

from gw_common.eval.runner import collect_evidence
from gw_common.evidence import drop_target, is_target_span
from gw_common.schemas import EvidenceCondition, EvidenceSpan, GoldItem, Label, Query

TARGET = "We achieved zero workplace fatalities in FY2024."


def span(text, company="Acme", year=2024, sid="s1"):
    return EvidenceSpan(statement_id=sid, text=text, company=company, year=year)


def query(target=TARGET, company="Acme", year=2024):
    return Query(text=target, company=company, anchor_year=year, target_text=target)


def test_same_sentence_same_report_is_target():
    assert is_target_span(span("we achieved ZERO workplace fatalities in FY2024"), query())


def test_chunk_containing_the_sentence_is_target():
    chunk = f"Safety is our priority. {TARGET} We will keep training staff."
    assert is_target_span(span(chunk), query())


def test_other_year_or_company_is_not_target():
    assert not is_target_span(span(TARGET, year=2023), query())
    assert not is_target_span(span(TARGET, company="Other"), query())


def test_short_target_needs_equality():
    q = query(target="Zero incidents.")
    assert is_target_span(span("zero incidents"), q)
    assert not is_target_span(span("There were zero incidents of corruption."), q)


def test_no_target_text_excludes_nothing():
    q = Query(text=TARGET, company="Acme", anchor_year=2024)
    assert not is_target_span(span(TARGET), q)


def test_harness_drops_target_and_counts_it():
    leaked = span(TARGET, sid="leak")
    other = span("Training hours rose to 20 per employee.", sid="ok")

    class Retriever:
        def retrieve(self, q, *, k=10):
            return [leaked, other]

    class System:
        def retriever(self):
            return Retriever()

    item = GoldItem(item_id="1", text=TARGET, company="Acme", year=2024,
                    gold_label=Label.IMPLEMENTED, label_source="test")
    evidence, dropped = collect_evidence(System(), [item], EvidenceCondition.SAME_REPORT_RRF)
    assert [s.statement_id for s in evidence["1"]] == ["ok"]
    assert dropped == 1
    kept, n = drop_target([other], query())
    assert kept == [other] and n == 0


def test_a3cg_reader_one_row_per_aspect(tmp_path):
    import json

    from gw_common.datasets import _read_a3cg

    recs = [
        {"text": "We cut water use and plan solar.", "sentence_id": 7,
         "aspect_categories": {"resource optimisation": ["water use", "solar"]},
         "aspects": {"water use": ["implemented"], "solar": ["planning"]}},
        {"text": "Revenue grew.", "sentence_id": 8,
         "aspect_categories": {"no aspect category": ["no aspect"]}, "aspects": {"no aspect": ["no action"]}},
        {"text": "Recycling, recycling.", "sentence_id": 9,
         "aspect_categories": {"waste management": ["recycling"]},
         "aspects": {"recycling": ["implemented", "planning"]}},
    ]
    path = tmp_path / "t.json"
    path.write_text(json.dumps(recs), encoding="utf-8")
    items, skipped = _read_a3cg(path)
    assert [(i.item_id, i.aspect, i.gold_label) for i in items] == [
        ("7:0", "water use", Label.IMPLEMENTED), ("7:1", "solar", Label.PLANNING), ("8:0", None, Label.NONE)]
    assert items[0].category == "resource optimisation"
    assert skipped == 1


def test_slices_and_selection():
    from gw_common.eval.select import parse_slices, select

    def item(i, split, row_type, cat):
        return GoldItem(item_id=str(i), text=f"s{i}", company="Acme", year=2024,
                        category=cat, gold_label=Label.IMPLEMENTED, label_source="test",
                        split=split, meta={"row_type": row_type})

    items = [item(1, "dev", "aspect", "workplace"), item(2, "test", "aspect", "workplace"),
             item(3, "dev", "no_aspect", None), item(4, "dev", "aspect", "outreach")]
    assert [i.item_id for i in select(items, split="dev")] == ["1", "3", "4"]
    picked = select(items, split="dev", slices=parse_slices("row_type=aspect"))
    assert [i.item_id for i in picked] == ["1", "4"]
    picked = select(items, slices=parse_slices("category=workplace|outreach"))
    assert [i.item_id for i in picked] == ["1", "2", "4"]
    assert len(select(items, sample=2, seed=1)) == 2
    try:
        parse_slices("nonsense=1")
    except ValueError as exc:
        assert "nonsense" in str(exc)
    else:
        raise AssertionError("unknown slice key must raise")


def test_majority_vote_and_instability():
    from gw_common.eval.runner import instability, majority_labels

    runs = [[Label.IMPLEMENTED, Label.PLANNING], [Label.IMPLEMENTED, Label.NONE],
            [Label.INDETERMINATE, Label.NONE]]
    assert majority_labels(runs) == [Label.IMPLEMENTED, Label.NONE]
    assert instability(runs) == {"unstable_items": 2, "unstable_share": 1.0}
    assert instability([[Label.NONE]]) == {"unstable_items": None, "unstable_share": None}


def test_exchange_round_trip(tmp_path):
    from gw_common.eval.exchange import export_queries, read_evidence, read_predictions
    from gw_common.schemas import EvidenceCondition

    items = [GoldItem(item_id="1", text=TARGET, aspect="fatalities", company="Acme", year=2024,
                      gold_label=Label.IMPLEMENTED, label_source="test")]
    q = tmp_path / "q.jsonl"
    info = export_queries(items, EvidenceCondition.CROSS_YEAR_RRF, q, k=3)
    assert info["queries"] == 1
    payload = json.loads(q.read_text(encoding="utf-8").strip())
    assert payload["anchor_year"] == 2024 and payload["year_from"] is None
    assert "gold" not in payload and "label" not in payload

    (tmp_path / "e.jsonl").write_text(
        json.dumps({"item_id": "1", "spans": [{"text": "prior year text", "company": "Acme",
                                               "year": 2023}]}) + "\n", encoding="utf-8")
    spans = read_evidence(tmp_path / "e.jsonl")
    assert spans["1"][0].year == 2023 and spans["1"][0].why == "external"

    (tmp_path / "p.jsonl").write_text(
        json.dumps({"item_id": "1", "label": "Planning"}) + "\n", encoding="utf-8")
    assert read_predictions(tmp_path / "p.jsonl")["1"].label is Label.PLANNING
