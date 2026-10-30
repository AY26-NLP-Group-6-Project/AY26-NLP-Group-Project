"""The corpus tools over the statement store, and the promise_window condition that any retriever serves."""

import json
from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest
from baseline_rag import chunks as chunk_store
from baseline_rag.corpus import ChunkCorpus
from baseline_rag.retrieve import supported_conditions
from graph_rag.promises import evidence as V
from gw_common.corpus import Corpus
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query

ROWS = [  # (stmt_id, company, year, page, text): report order, as the statement store keeps it
    ("aaaa0001p0003s000", "Acme", 2022, 3, "We aim to cut the accident frequency rate to zero by 2023."),
    ("aaaa0001p0003s001", "Acme", 2022, 3, "Water use fell across the group during the year."),
    ("bbbb0001p0002s000", "Acme", 2023, 2, "Occupational health and safety accident frequency rate of zero."),
    ("bbbb0001p0002s001", "Acme", 2023, 2, "Requires improvement: two cases were recorded."),
    ("bbbb0001p0005s000", "Acme", 2023, 5, "Energy use per square foot was unchanged from last year."),
    ("cccc0001p0001s000", "Other", 2023, 1, "The accident frequency rate at Other stayed at zero in 2023."),
]


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    store = tmp_path / "store" / "statements"
    store.mkdir(parents=True)
    with (store / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for sid, company, year, page, text in ROWS:
            chunk = chunk_store.Chunk(
                chunk_id=sid,
                text=text,
                company=company,
                year=year,
                page=page,
                file=sid[:8],
                statement_ids=[sid],
            )
            f.write(json.dumps(asdict(chunk)) + "\n")
    np.save(store / "embeddings.npy", np.eye(len(ROWS), 8, dtype=np.float32))
    (store / "manifest.json").write_text(
        json.dumps({"chunks": len(ROWS), "unit": "statement", "chunks_sha256": "abc"}), encoding="utf-8"
    )
    monkeypatch.setattr(chunk_store, "STORE_ROOT", tmp_path / "store")
    client = SimpleNamespace(embed=lambda texts: [[1.0] + [0.0] * 7 for _ in texts])
    return ChunkCorpus("statements", client=client)


def test_corpus_tools_search_read_around_and_list_reports(corpus):
    assert isinstance(corpus, Corpus)
    hits = corpus.search("accident frequency rate", company="Acme", year_from=2023, k=3, mode="bm25")
    assert hits and hits[0].statement_id == "bbbb0001p0002s000" and all(h.year == 2023 for h in hits)
    assert corpus.search("accident", company="Acme", exclude_year=2023, mode="bm25")[0].year == 2022
    assert corpus.search("accident", company="Nobody", mode="bm25") == []
    with pytest.raises(ValueError):
        corpus.search("accident", mode="magic")
    assert corpus.get("bbbb0001p0002s001").text.startswith("Requires improvement")
    assert corpus.get("missing") is None
    around = corpus.neighbours("bbbb0001p0002s001", before=1, after=1)
    assert [s.statement_id for s in around] == ["bbbb0001p0002s000", "bbbb0001p0002s001"]  # same page only
    assert [s.statement_id for s in corpus.page("Acme", 2023, 5)] == ["bbbb0001p0005s000"]
    reports = corpus.reports("Acme")
    assert [(r.year, r.pages, r.statements) for r in reports] == [(2022, 3, 2), (2023, 5, 3)]
    assert corpus.companies() == ["Acme", "Other"]
    assert corpus.describe()["corpus"] == "statements"


def test_promise_window_is_a_supported_condition_with_the_window_on_the_query():
    assert EvidenceCondition.PROMISE_WINDOW in supported_conditions()
    assert Query(text="x").meta == {}
    promise = {
        "promise_id": "P1",
        "company": "Acme",
        "metric": "accident frequency rate",
        "target_year": 2023,
        "related": [],
        "origin": {
            "year": 2021,
            "page": 3,
            "text": "We aim for zero by 2023.",
            "target_text": "zero accidents by 2023",
        },
    }
    q = V.promise_query(promise)
    assert (q.company, q.year_from, q.year_to, q.anchor_year) == ("Acme", 2022, 2024, 2021)
    assert q.condition is EvidenceCondition.PROMISE_WINDOW and q.meta["promise"] is promise
    assert V.promise_of(q) is promise
    bare = Query(
        text="accident frequency rate",
        company="Acme",
        aspect="accident frequency rate",
        year_from=2022,
        year_to=2024,
        anchor_year=2021,
        condition=EvidenceCondition.PROMISE_WINDOW,
    )
    rebuilt = V.promise_of(bare)
    assert rebuilt["target_year"] == 2023 and rebuilt["origin"]["year"] == 2021 and rebuilt["related"] == []


def test_spans_round_trip_into_evidence_rows_with_follows(corpus):
    spans = [
        corpus.get("bbbb0001p0002s001"),
        corpus.get("aaaa0001p0003s000"),
        corpus.get("bbbb0001p0002s000"),
    ]
    rows = V.evidence_of(spans)
    assert [r["ref"] for r in rows] == ["E1", "E2", "E3"]
    assert [r["stmt_id"] for r in rows] == ["aaaa0001p0003s000", "bbbb0001p0002s000", "bbbb0001p0002s001"]
    assert rows[2]["follows"] == "E2" and "follows" not in rows[1]
    back = V.spans_of(rows, "Acme")
    assert isinstance(back[0], EvidenceSpan) and back[0].why.startswith("trajectory:")


def test_build_from_system_writes_the_evidence_file_named_after_the_system(tmp_path, monkeypatch, corpus):
    monkeypatch.setattr(V, "out_dir", lambda cfg: tmp_path)
    promise = {
        "promise_id": "P1",
        "company": "Acme",
        "metric": "accident frequency rate",
        "target_year": 2023,
        "checkable": True,
        "related": [],
        "stated_in_years": [2022],
        "origin": {
            "year": 2022,
            "page": 3,
            "text": "We aim to cut the accident frequency rate to zero by 2023.",
            "target_text": "cut the accident frequency rate to zero by 2023",
        },
    }
    (tmp_path / "promises.jsonl").write_text(json.dumps(promise) + "\n", encoding="utf-8")

    class FakeRetriever:
        def retrieve(self, query, *, k=10):
            assert query.condition is EvidenceCondition.PROMISE_WINDOW
            return corpus.search(
                query.text,
                company=query.company,
                year_from=query.year_from,
                year_to=query.year_to,
                k=k,
                mode="bm25",
            )

        def describe(self):
            return {"store": "fake"}

    system = SimpleNamespace(
        name="fake-rag",
        supported_conditions=lambda: [EvidenceCondition.PROMISE_WINDOW],
        retriever=lambda: FakeRetriever(),
    )
    stats = V.build_from_system(None, system, k=5)
    assert stats["mode"] == "fake-rag" and stats["promises"] == 1 and stats["retriever"] == {"store": "fake"}
    rows = json.loads((tmp_path / "evidence.fake-rag.jsonl").read_text(encoding="utf-8"))
    assert rows["promise_id"] == "P1" and all(e["year"] == 2023 for e in rows["evidence"])
    assert rows["evidence"][0]["ref"] == "E1" and rows["evidence"][1].get("follows") == "E1"
    other = SimpleNamespace(name="no-window", supported_conditions=lambda: [], retriever=lambda: None)
    with pytest.raises(ValueError):
        V.build_from_system(None, other)
