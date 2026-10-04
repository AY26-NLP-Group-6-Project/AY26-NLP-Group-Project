"""RQ2 plumbing: target validation, merging restatements into promises, checkability, the outcome
rule, sheet scoring."""

import json
import re
import zlib
from types import SimpleNamespace

import numpy as np
import pytest
from graph_rag.promises import build as B
from graph_rag.promises import evidence as V
from graph_rag.promises import extract as E
from graph_rag.promises import outcome as O
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
    # as reported, failed and revised are one class
    assert result["reported"]["human_distribution"] == {"achieved": 1, "not_met": 2}
    assert result["reported"]["per_class"]["not_met"] == {"precision": 1.0, "recall": 0.5, "support": 2}
    assert O.reported("revised") == O.reported("failed") == "not_met" and O.reported("unclear") == "unclear"
    assert S.agreement(["failed", "revised"], ["revised", "revised"], O.OUTCOMES)["accuracy"] == 0.5
    assert S.agreement(["not_met", "not_met"], ["not_met", "not_met"], O.REPORTED)["accuracy"] == 1.0

    # the same sheet scored against another judge's output over the same promises
    judged = [{"promise_id": "P1", "outcome": "achieved"}, {"promise_id": "P2", "outcome": "unclear"},
              {"promise_id": "P3", "outcome": "failed"}, {"promise_id": "P4", "outcome": "unclear"}]
    other = tmp_path / "outcomes.v2.jsonl"
    other.write_text("\n".join(json.dumps(o) for o in judged), encoding="utf-8")
    again = S.score(None, path, outcomes=other)
    assert again["outcome"]["accuracy"] == pytest.approx(2 / 3)
    assert again["outcome"]["under_commitment"] == {"k": 1, "n": 3, "rate": pytest.approx(1 / 3)}
    assert again["outcome"]["over_commitment"] == {"k": 0, "n": 0, "rate": None}
    assert again["outcome"]["verdict_precision"] == {"k": 2, "n": 2, "rate": 1.0}
    assert (tmp_path / "promise_check_result.outcomes.v2.json").exists()
    assert S.sheet_ids(path) == {"P1", "P2", "P3", "P4"}


def test_population_weights_each_stratum_by_the_pool_it_was_drawn_from():
    # 100 promises proposed achieved, 10 proposed failed; the sheet took 4 and 4
    strata = {"achieved": [("achieved", "achieved")] * 3 + [("unclear", "achieved")],
              "failed": [(h, "failed") for h in ("failed", "revised", "unclear", "failed")]}
    flat = [pair for pairs in strata.values() for pair in pairs]
    assert sum(h == s for h, s in flat) / len(flat) == pytest.approx(0.625)     # the sheet's raw rate
    est = S.population(strata, {"achieved": 100, "failed": 10, "unclear": 50}, draws=200)
    assert est["pool"] == 110                                                   # no row drawn from "unclear"
    # reported classes: the row the annotator called revised and the system failed is "not met" twice
    assert est["accuracy"]["estimate"] == pytest.approx((100 * 0.75 + 10 * 0.75) / 110)
    assert est["accuracy_five_way"]["estimate"] == pytest.approx((100 * 0.75 + 10 * 0.5) / 110)
    # every promise the annotator called unclear got a verdict from the system
    assert est["over_commitment"]["estimate"] == pytest.approx(1.0)
    assert est["human_share.unclear"]["estimate"] == pytest.approx((100 * 0.25 + 10 * 0.25) / 110)
    assert est["human_share.not_met"]["estimate"] == pytest.approx(10 * 0.75 / 110)
    low, high = est["accuracy"]["ci95"]
    assert low <= est["accuracy"]["estimate"] <= high


def label(ref, relation="other", result="none", change="none", year=None):
    return {"ref": ref, "year": year, "relation": relation, "deadline_result": result, "change": change}


def test_decide_needs_a_statement_about_this_target_that_states_the_outcome():
    this = "this_target"
    assert O.decide([label("E1", this, "met")], annual=False) == ("achieved", ["E1"])
    assert O.decide([label("E1", this, "missed")], annual=False) == ("failed", ["E1"])
    assert O.decide([label("E1", this, change="later")], annual=False) == ("revised", ["E1"])
    # an annual target set again for a later year is renewal, not a moved goalpost
    assert O.decide([label("E1", this, change="later")], annual=True) == ("unclear", ["E1"])
    # a moved goalpost explains a miss; a reported result beats a restatement
    both = [label("E1", this, "missed"), label("E2", this, change="later")]
    assert O.decide(both, annual=False) == ("revised", ["E2"])
    assert O.decide(both, annual=True) == ("failed", ["E1"])
    kept = [label("E1", this, "met"), label("E2", this, change="later")]
    assert O.decide(kept, annual=False) == ("achieved", ["E1"])
    # contradictory results, or statements about the metric only, settle nothing
    assert O.decide([label("E1", this, "met"), label("E2", this, "missed")], annual=False)[0] == "unclear"
    assert O.decide([label("E1", "same_metric"), label("E2")], annual=False) == ("unclear", ["E1"])
    assert O.decide([label("E1"), label("E2")], annual=False) == ("disappeared", [])


def test_decide_keeps_to_the_calendar_when_the_evidence_spans_earlier_years():
    this = "this_target"
    restated = label("E1", this, year=2022)                 # repeated before the 2024 deadline
    # ... and never mentioned from the deadline year on: it has disappeared
    assert O.decide([restated, label("E2", year=2024)], annual=False, deadline=2024) == ("disappeared", [])
    assert O.decide([restated, label("E2", "same_metric", year=2025)], False, 2024) == ("unclear", ["E2"])
    # a report older than the deadline cannot say the deadline was missed
    assert O.decide([label("E1", this, "missed", year=2023)], False, 2024)[0] == "disappeared"
    assert O.decide([label("E1", this, "missed", year=2024)], False, 2024) == ("failed", ["E1"])
    # it can report a deliverable finished early, but not an annual target's deadline-year result
    assert O.decide([label("E1", this, "met", year=2023)], False, 2024) == ("achieved", ["E1"])
    assert O.decide([label("E1", this, "met", year=2023)], True, 2024)[0] == "disappeared"
    # a deadline moved in an earlier report is a revision, unless the original was then reported met
    moved = label("E1", this, change="later", year=2022)
    assert O.decide([moved], False, 2024) == ("revised", ["E1"])
    assert O.decide([moved, label("E2", this, "met", year=2024)], False, 2024) == ("achieved", ["E2"])


def test_parse_labels_keeps_verdict_fields_only_on_this_target_and_flags_gaps():
    evidence = [{"ref": "E1"}, {"ref": "E2"}]
    given = [{"ref": "E1", "relation": "same_metric", "deadline_result": "missed", "change": "later"},
             {"ref": "[e2]", "relation": "This_Target", "deadline_result": "met", "change": "none"}]
    labels, complete = O.parse_labels({"annual": False, "evidence": given}, evidence)
    assert complete
    assert labels[0] == label("E1", "same_metric") and labels[1] == label("E2", "this_target", "met")
    assert not O.parse_labels({"annual": False, "evidence": given[:1]}, evidence)[1]   # a statement left out
    assert not O.parse_labels({"evidence": given}, evidence)[1]                        # no annual flag
    assert O.vote(["failed", "failed", "unclear"]) == "failed"
    assert O.vote(["failed", "revised", "unclear"]) == "unclear"


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        return type("Reply", (), {"text": self.replies.pop(0)})()


def test_propose_v2_retries_a_garbled_reply_and_reads_renewal_as_no_verdict():
    prompt = O._sections(O.PROMPTS["v2"])
    promise = {**target("a", "Acme", 2022, "incidents", 2023),
               "origin": {"year": 2022, "page": 3, "text": STATEMENT}}
    evidence = [{"ref": "E1", "year": 2024, "page": 3, "text": "We aim for zero incidents in FY2024."}]
    good = json.dumps({"annual": False, "rationale": "restated for a later year", "outcome": "revised",
                       "evidence": [label("E1", "this_target", change="later")]})
    client = FakeClient(["", good])
    out = O.propose_v2(promise, evidence, client, prompt)
    assert client.calls == 2 and out["parse_ok"]
    assert out["outcome"] == "revised" and out["evidence_refs"] == ["E1"]
    assert out["model_outcome"] == "revised"
    # the extraction already marked it as an annual target: the same reply is a renewal
    out = O.propose_v2({**promise, "recurring": True}, evidence, FakeClient([good]), prompt)
    assert out["outcome"] == "unclear" and out["annual"]
    out = O.propose_v2(promise, evidence, FakeClient(["", "not json"]), prompt)
    assert out["outcome"] == "unclear" and not out["parse_ok"]
    assert O.propose_v2(promise, [], FakeClient([]), prompt)["outcome"] == "disappeared"


class FakeEmbedder:
    """Deterministic bag-of-words vectors, so dense ranking works without a model."""

    def embed(self, texts):
        out = np.zeros((len(texts), 64), dtype=np.float32)
        for i, text in enumerate(texts):
            for token in re.findall(r"[a-z]+", text.lower()):
                out[i, zlib.crc32(token.encode()) % 64] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1.0, norms)


REPORTS = {
    2021: ["We aim to cut the accident frequency rate to zero by 2023."],
    2022: ["Our accident frequency rate target remains zero by 2023 for all sites.",
           "The accident frequency rate was reviewed by the board twice.",
           "Water use fell across the group during the year.",
           "We planted trees in the community garden last spring.",
           "Group safety ambition restated for 2026 under the new plan."],
    2023: ["Occupational health and safety accident frequency rate of zero.",
           "Requires improvement: two cases.",
           "Energy use per square foot was unchanged from last year.",
           "The board met four times during the financial year.",
           "Staff volunteered at the food bank in December again."],
    2024: ["The accident frequency rate target of zero is now set for 2025 instead."],
    2025: ["In 2025 the accident frequency rate was zero again this year."],
}


def test_trajectory_evidence_follows_the_promise_through_the_later_reports(tmp_path):
    from graph_rag.store.duckdb_store import DuckDBGraphStore

    db = tmp_path / "graph.duckdb"
    store = DuckDBGraphStore(db)
    for year, texts in REPORTS.items():
        for idx, text in enumerate(texts):
            store.con.execute(
                "INSERT INTO statements (stmt_id, sha256, company, year, page, idx, text, norm_text, source) "
                "VALUES (?, ?, 'Acme', ?, 9, ?, ?, ?, 'corpus')",
                [f"r{year}p0009s{idx:03d}", f"sha{year}", year, idx, text, text.lower()])
    store.con.close()
    promise = {"promise_id": "P1", "company": "Acme", "metric": "accident frequency rate",
               "target_year": 2023,
               "origin": {"year": 2021, "target_text": "cut the accident frequency rate to zero by 2023"},
               "related": [{"promise_id": "P2"}, {"promise_id": "gone"}]}
    other = {"promise_id": "P2", "target_year": 2026,
             "origin": {"stmt_id": "r2022p0009s004", "year": 2022, "page": 9, "file": "sha2022",
                        "text": REPORTS[2022][4]}}
    finder = V.TrajectoryFinder(SimpleNamespace(db_path=db), FakeEmbedder(), {"P1": promise, "P2": other},
                                sentence_store="no-such-store")
    evidence = finder.find(promise)

    assert finder.window(promise) == [2022, 2023, 2024]              # after the promise, up to deadline + 1
    assert [e["ref"] for e in evidence] == [f"E{n}" for n in range(1, len(evidence) + 1)]
    assert [e["year"] for e in evidence] == sorted(e["year"] for e in evidence)
    assert not any(e["year"] in (2021, 2025) for e in evidence)
    by_text = {e["text"]: e for e in evidence}
    # an earlier report gets a small budget, plus the target the promise graph links to it
    assert [e["via"] for e in evidence if e["year"] == 2022].count("retrieved") == V.K_BEFORE
    assert by_text[REPORTS[2022][4]]["via"] == "linked"
    # the cell beside the target row is too short to be retrieved and comes in as its neighbour
    result, row = by_text["Requires improvement: two cases."], by_text[REPORTS[2023][0]]
    assert result["via"] == "neighbour" and result["follows"] == row["ref"]
    assert V.where(result) == f"2023 report, p.9, directly follows {row['ref']}"
    assert REPORTS[2024][0] in by_text

    cell = S.evidence_cell(evidence, deadline=2023)
    assert "—— 2022 report (before the deadline) ——" in cell and "—— 2023 report (deadline year) ——" in cell
    assert f"[{result['ref']}] 2023 report, p.9, directly follows {row['ref']}: Requires improvement" in cell
    assert S.evidence_cell([], deadline=2023) == "(nothing retrieved)"
