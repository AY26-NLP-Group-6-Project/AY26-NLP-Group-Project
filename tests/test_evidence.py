from gw_common.eval.runner import _collect_evidence
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
    evidence, dropped = _collect_evidence(System(), [item], EvidenceCondition.SAME_REPORT_RRF)
    assert [s.statement_id for s in evidence["1"]] == ["ok"]
    assert dropped == 1
    kept, n = drop_target([other], query())
    assert kept == [other] and n == 0
