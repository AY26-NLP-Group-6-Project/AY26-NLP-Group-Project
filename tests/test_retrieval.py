"""Pooled retrieval evaluation: the query set is seeded, the judge is faked, the run is publishable."""

import json

import pytest
from gw_common.eval import relevance as RJ
from gw_common.eval import retrieval as R
from gw_common.eval.compare import publish, write_index
from gw_common.llm import ChatResult, LLMSettings
from gw_common.schemas import EvidenceCondition, EvidenceSpan, GoldItem, Label


def _item(i: int, company: str, aspect: str | None, category: str | None, year: int = 2024) -> GoldItem:
    return GoldItem(item_id=str(i), text=f"Sentence {i} about {aspect or 'nothing'}.", aspect=aspect,
                    category=category, company=company, year=year, page=i, gold_label=Label.PLANNING,
                    label_source="test", split="dev")


ITEMS = [_item(1, "Acme", "solar panels", "emissions control"),
         _item(2, "Acme", "solar panels", "emissions control", 2023),
         _item(3, "Acme", "water use", "resource optimisation"),
         _item(4, "Bolt", "training hours", "workplace"),
         _item(5, "Bolt", "a rejected aspect", None),           # a `none` row: not a query
         _item(6, "Cord", "board diversity", "management")]


def test_build_queries_is_seeded_typed_and_reads_no_none_rows():
    plan = {"company_claim": 2, "cross_year_aspect": 2, "generic": 3}
    a = R.build_queries(ITEMS, plan=plan)
    assert a == R.build_queries(ITEMS, plan=plan)
    by_type = {t: [q for q in a if q["type"] == t] for t in R.QUERY_TYPES}
    assert [len(by_type[t]) for t in R.QUERY_TYPES] == [2, 2, 3]
    claim = by_type["company_claim"][0]
    assert claim["anchor_year"] and claim["target_text"] == claim["text"] and claim["company"]
    aspect = by_type["cross_year_aspect"][0]
    assert "anchor_year" not in aspect and aspect["text"] == aspect["aspect"]
    assert all("company" not in q for q in by_type["generic"])
    assert all(q.get("item_id") != "5" for q in a)
    # a (company, aspect) pair is one aspect query, and never one already asked as a claim
    claimed = {q["item_id"] for q in by_type["company_claim"]}
    assert not claimed & {q["item_id"] for q in by_type["cross_year_aspect"]}


def test_mode_specs_name_the_system_and_the_graph_conditions():
    assert R.parse_mode("bm25", "baseline-rag") == ("baseline-rag", "bm25", None)
    assert R.parse_mode("graph-rag:graph", "baseline-rag") == (
        "graph-rag", "graph", EvidenceCondition.CROSS_YEAR_GRAPH)
    assert R.parse_mode("graph-rag:fused", None)[2] is EvidenceCondition.CROSS_YEAR_FUSED
    with pytest.raises(ValueError):
        R.parse_mode("bm25", None)


def _span(doc: str, company: str = "Acme", year: int = 2023) -> EvidenceSpan:
    return EvidenceSpan(statement_id=doc, text=f"text of {doc}", company=company, year=year, page=1)


QUERIES = [{"query_id": "q1", "type": "company_claim", "text": "solar", "company": "Acme",
            "anchor_year": 2024},
           {"query_id": "q2", "type": "generic", "text": "water"}]
RESULTS = {
    "bm25": {"q1": [_span("d1"), _span("d2"), _span("d3")], "q2": [_span("d7"), _span("d8")]},
    "rrf+rerank": {"q1": [_span("d2"), _span("d1"), _span("d9", company="Bolt")], "q2": [_span("d8")]},
    "graph-rag:graph": {"q1": [_span("d1")], "q2": []},
}
QRELS = {"q1": {"d1": 3, "d2": 1, "d3": 0, "d9": 2}, "q2": {"d7": 2, "d8": 0}}


def test_score_honours_the_minimum_grade_and_breaks_down_by_type():
    strict = R.score(RESULTS["bm25"], QRELS, QUERIES, min_grade=2)
    q1 = next(r for r in strict["per_query"] if r["query_id"] == "q1")
    assert q1["relevant_in_pool"] == 2 and q1["mrr"] == 1.0 and q1["r_at_10"] == pytest.approx(0.5)
    assert q1["p_at_5"] == pytest.approx(0.2) and q1["wrong_company_at_10"] == 0.0
    lenient = R.score(RESULTS["bm25"], QRELS, QUERIES, min_grade=1)
    assert next(r for r in lenient["per_query"] if r["query_id"] == "q1")["relevant_in_pool"] == 3
    assert set(strict["by_type"]) == {"company_claim", "generic"}
    generic = strict["by_type"]["generic"]
    assert generic["n"] == 1 and generic["wrong_company_at_10"] is None
    # a configuration that returns nothing for a query scores 0 on it, and says it returned nothing
    graph = R.score(RESULTS["graph-rag:graph"], QRELS, QUERIES)
    assert next(r for r in graph["per_query"] if r["query_id"] == "q2")["returned"] == 0


def test_paired_comparison_is_on_the_same_queries():
    scores = {c: R.score(pq, QRELS, QUERIES) for c, pq in RESULTS.items()}
    against = R.compare_configs(scores, "rrf+rerank")
    assert set(against) == {"bm25", "graph-rag:graph"} and against["bm25"]["n"] == 2
    assert against["bm25"]["wins"] + against["bm25"]["losses"] <= 2
    assert R.compare_configs(scores, "rrf+rerank", types=["company_claim"])["bm25"]["n"] == 1


class _FakeJudge:
    """Grades D1 high, D2 low, forgets the rest; the second reply (JSON-forced) is the same."""

    settings = LLMSettings(chat_model="fake-judge")
    usage = {"calls": 0, "cache_hits": 0, "input_tokens": 10, "output_tokens": 5}

    def __init__(self) -> None:
        self.prompts = []

    def chat(self, messages, **_):
        self.prompts.append(messages[1]["content"])
        self.usage["calls"] += 1
        reply = {"grades": [{"ref": "D1", "grade": 3, "reason": "same target"},
                            {"ref": "[D2]", "grade": "0", "reason": "another topic"},
                            {"ref": "D99", "grade": 2, "reason": "no such result"}]}
        return ChatResult(text="Here you go:\n" + json.dumps(reply), model="fake-judge")


def test_the_judge_grades_a_pool_and_writes_qrels_the_scorer_reads(tmp_path):
    pool = [{"query_id": "q1", "query_type": "company_claim", "query": "solar", "company": "Acme",
             "doc_id": d, "doc_company": "Acme", "doc_year": "2023", "doc_page": "1", "text": f"text of {d}",
             "first_seen_config": "bm25", "first_rank": str(i), "relevant": ""}
            for i, d in enumerate(["d1", "d2", "d3"], 1)]
    client = _FakeJudge()
    judge = RJ.RelevanceJudge(client=client, workers=1)
    graded, summary = judge.judge(pool, QUERIES)
    assert graded["q1"]["d1"] == {"grade": 3, "reason": "same target"}
    assert graded["q1"]["d2"]["grade"] == 0 and graded["q1"]["d3"]["reason"] == RJ.UNJUDGED
    assert summary["documents"] == 3 and summary["unjudged"] == 1 and summary["calls"] == 1
    assert summary["grade_counts"] == {"not relevant": 2, "marginal": 0, "relevant": 0, "highly relevant": 1}
    assert "years: the company's report years other than 2024" in client.prompts[0]
    assert "[D3] (Acme, 2023, p.1) text of d3" in client.prompts[0]

    out = RJ.write_qrels(graded, tmp_path / "qrels.jsonl", judge.describe())
    assert R.load_qrels(out) == {"q1": {"d1": 3, "d2": 0, "d3": 0}}
    meta = RJ.load_qrels_meta(out)
    assert meta["judge"] == "llm" and meta["model"] == "fake-judge" and meta["prompt"] == "relevance_judge.md"


def test_the_pool_sheet_round_trips_through_the_judge_loader(tmp_path):
    info = R.export_pool(RESULTS, QUERIES, tmp_path / "pool.csv")
    rows = RJ.load_pool(tmp_path / "pool.csv")
    assert info["pooled_documents"] == len(rows) == 6          # d1 d2 d3 d9 for q1, d7 d8 for q2
    assert {r["doc_id"] for r in rows if r["query_id"] == "q1"} == {"d1", "d2", "d3", "d9"}
    assert rows[0]["relevant"] == ""                            # the sheet is blind


def test_a_scored_run_is_written_and_publishable(tmp_path):
    queries_path = tmp_path / "queries.jsonl"
    queries_path.write_text("".join(json.dumps(q) + "\n" for q in QUERIES), encoding="utf-8")
    qrels_path = tmp_path / "qrels.jsonl"
    judge = {"judge": "llm", "model": "m"}
    qrels_path.write_text("".join(json.dumps({"query_id": q, "relevant": d, "judge": judge}) + "\n"
                                  for q, d in QRELS.items()), encoding="utf-8")
    run = R.write_run(RESULTS, QUERIES, QRELS, queries_path=queries_path, qrels_path=qrels_path,
                      retrievers={"bm25": {"store": "statements", "chunks_sha256": "abc", "mode": "bm25"}},
                      judge_info={"judge": "llm", "model": "m", "prompt": "relevance_judge.md"},
                      out_root=tmp_path / "runs")
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    assert manifest["task"] == "retrieval" and manifest["system"] == "baseline-rag+graph-rag"
    assert manifest["config"]["retriever"]["store"] == "statements" and manifest["label_source"] == "llm"
    assert metrics["reference"] == "rrf+rerank" and set(metrics["configs"]) == set(RESULTS)
    assert metrics["configs"]["bm25"]["min_grade"] == 2
    assert metrics["configs_lenient"]["bm25"]["min_grade"] == 1
    assert "bm25" in metrics["against_reference"]
    report = (run / "report.md").read_text(encoding="utf-8")
    assert "Model-judged relevance" in report and "| `graph-rag:graph` |" in report
    assert len((run / "rankings.jsonl").read_text(encoding="utf-8").splitlines()) == 6

    results = tmp_path / "results"
    out = publish(run, results, "pooled retrieval metrics", name="retrieval/dev-pooled")
    index = write_index(results).read_text(encoding="utf-8")
    assert (out / "report.md").exists() and not (out / "rankings.jsonl").exists()
    link = "[retrieval/dev-pooled](retrieval/dev-pooled/report.md)"
    assert f"| {link} | baseline-rag+graph-rag | judge-relevance" in index
    assert "| — | — | pooled retrieval metrics |" in index
