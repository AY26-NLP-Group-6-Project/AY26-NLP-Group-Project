"""Hand-checked behaviour of the hybrid baseline's stages."""

import json
from dataclasses import asdict

import numpy as np
import pytest

from baseline_rag import chunks as chunk_store
from baseline_rag.index import BM25, Dense, rrf
from gw_common.schemas import EvidenceCondition, Query

duckdb = pytest.importorskip("duckdb")

DOCS = [
    "We reduced water consumption at our plants by twelve per cent this year.",
    "The board approved an anti-corruption policy covering all subsidiaries.",
    "Water recycling equipment was installed at the Johor site.",
]


def test_bm25_ranks_the_matching_document_first():
    idx = BM25(DOCS)
    assert idx.search("water recycling")[0][0] == 2
    assert idx.search("anti-corruption policy")[0][0] == 1


def test_bm25_honours_the_allowed_set():
    idx = BM25(DOCS)
    assert [i for i, _ in idx.search("water", allowed={0})] == [0]
    assert idx.search("water", allowed=set()) == []


def test_dense_cosine_and_filter():
    vectors = np.array([[1.0, 0.0], [0.0, 1.0], [0.7071, 0.7071]], dtype=np.float32)
    dense = Dense(vectors)
    assert dense.search([1.0, 0.0])[0][0] == 0
    assert [i for i, _ in dense.search([1.0, 0.0], allowed={1, 2})][0] == 2


def test_rrf_prefers_what_both_rankers_like():
    a = [(1, 9.0), (2, 8.0), (3, 7.0)]
    b = [(3, 0.9), (1, 0.8), (4, 0.2)]
    fused = dict(rrf(a, b))
    assert max(fused, key=fused.get) in {1, 3}
    assert fused[1] == pytest.approx(1 / 61 + 1 / 62)
    assert fused[4] == pytest.approx(1 / 63)


def _tiny_db(tmp_path, statements):
    path = tmp_path / "g.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE statements (sha256 VARCHAR, company VARCHAR, year INTEGER, "
                "page INTEGER, idx INTEGER, stmt_id VARCHAR, text VARCHAR)")
    con.executemany("INSERT INTO statements VALUES (?, ?, ?, ?, ?, ?, ?)", statements)
    con.close()
    return path


def test_chunks_group_by_report_and_keep_provenance(tmp_path):
    prose = "We have reduced our Scope 1 emissions by twelve per cent compared with the prior year. "
    rows = [("sha1", "Acme", 2024, 3, i, f"s{i}", prose.strip()) for i in range(30)]
    rows += [("sha2", "Acme", 2023, 5, 0, "t0", prose.strip())]
    rows += [("sha1", "Acme", 2024, 3, 99, "junk", "GRI 102-54 Page 3 of 26")]
    built = chunk_store.build_chunks(_tiny_db(tmp_path, rows))
    assert len({c.file for c in built}) == 2
    assert all(len(c.text.split()) <= chunk_store.TARGET_WORDS + 20 for c in built)
    junk = [c for c in built if "GRI 102-54" in c.text]
    assert junk and junk[0].prose_ratio < 1.0  # page furniture is kept but marked, not silently dropped
    assert built[0].statement_ids and built[0].company == "Acme"
    assert built[0].indexed_text().startswith("Acme (2024), page 3:")


def test_store_round_trip_and_year_filters(tmp_path, monkeypatch):
    prose = "Our safety programme recorded zero incidents across all operating sites this year."
    rows = [("sha1", "Acme", 2024, 1, 0, "a", prose), ("sha2", "Acme", 2023, 1, 0, "b", prose),
            ("sha3", "Other", 2023, 1, 0, "c", prose)]
    built = chunk_store.build_chunks(_tiny_db(tmp_path, rows))
    store = tmp_path / "store" / "dev"
    store.mkdir(parents=True)
    with (store / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in built:
            f.write(json.dumps(asdict(c)) + "\n")
    np.save(store / "embeddings.npy", np.eye(len(built), 4, dtype=np.float32))
    (store / "manifest.json").write_text(json.dumps({"chunks": len(built)}), encoding="utf-8")
    monkeypatch.setattr(chunk_store, "STORE_ROOT", tmp_path / "store")

    from baseline_rag.retrieve import HybridRetriever

    r = HybridRetriever.__new__(HybridRetriever)  # no embedding client in tests
    r.chunks, vectors, r.manifest = chunk_store.load("dev")
    r.mode, r.reranker = "bm25", None
    r.bm25 = BM25([c.indexed_text() for c in r.chunks])
    r.dense = Dense(vectors)
    r._by_company = {}
    for i, c in enumerate(r.chunks):
        r._by_company.setdefault(c.company, []).append(i)

    q = Query(text=prose, company="Acme", anchor_year=2024, target_text=prose,
              condition=EvidenceCondition.CROSS_YEAR_RRF)
    spans = r.retrieve(q, k=5)
    assert [s.year for s in spans] == [2023]          # anchor year and other companies excluded
    assert all(s.company == "Acme" for s in spans)

    q_same = Query(text=prose, company="Acme", anchor_year=2024, year_from=2024, year_to=2024,
                   target_text=prose, condition=EvidenceCondition.SAME_REPORT_RRF)
    assert [s.year for s in r.retrieve(q_same, k=5)] == [2024]
