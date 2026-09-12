"""Graph store and build helpers, on a synthetic in-memory graph.

These tests must not need the corpus: they check the joins and the derived edges, which is what the
M1 gate is about. Corpus-scale numbers live in artifacts/graph/<build_id>/build_manifest.json.
"""

from graph_rag.build.derive import run as derive_run
from graph_rag.build.text import aspect_key, clean_page, normalise, split_sentences
from graph_rag.config import GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore


def _fixture_store(tmp_path):
    store = DuckDBGraphStore(tmp_path / "g.duckdb")
    store.insert_many("companies", [("Acme", "A1")], 2)
    store.insert_many(
        "reports",
        [("sha2023", "Acme", 2023, "raw/acme/2023.pdf", 10),
         ("sha2025", "Acme", 2025, "raw/acme/2025.pdf", 10)],
        5,
    )
    store.insert_many(
        "statements",
        [
            ("s1", "sha2023", "Acme", 2023, 4, 0, "We will install solar panels.",
             "we will install solar panels", "corpus"),
            ("s2", "sha2025", "Acme", 2025, 7, 1, "Our solar panels generated 500 MWh.",
             "our solar panels generated 500 mwh", "corpus"),
        ],
        9,
    )
    store.insert_many("aspects", [("solar panels", "solar panels", "resource optimisation", "gold_span")], 4)
    store.insert_many("aspect_aliases", [("solar panels", "solar panels", "gold_span")], 3)
    store.insert_many(
        "mentions",
        [("s1", "solar panels", "planning", "llm_pre", "gold_span"),
         ("s2", "solar panels", None, None, "string_match")],
        5,
    )
    return store


def test_chain_spans_two_years(tmp_path):
    store = _fixture_store(tmp_path)
    chains = store.chains(min_years=2)
    assert len(chains) == 1
    assert chains[0].years == [2023, 2025]
    assert store.chains(min_years=3) == []


def test_statements_for_is_year_filtered(tmp_path):
    store = _fixture_store(tmp_path)
    rows = store.statements_for("Acme", "solar panels")
    assert [r["year"] for r in rows] == [2023, 2025]
    assert rows[0]["action"] == "planning"
    assert [r["year"] for r in store.statements_for("Acme", "solar panels", year_from=2024)] == [2025]


def test_derive_links_consecutive_years(tmp_path):
    store = _fixture_store(tmp_path)
    cfg = GraphConfig(build_id="test")
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    stats = derive_run(cfg, store, verbose=False)
    assert stats["follows_up_edges"] == 1
    edge = store.con.execute(
        "SELECT from_stmt, to_stmt, years_apart, same_text FROM follows_up"
    ).fetchone()
    assert edge == ("s1", "s2", 2, False)
    assert stats["verbatim_repeat_edges"] == 0


def test_subgraph_has_statement_and_aspect_nodes(tmp_path):
    store = _fixture_store(tmp_path)
    g = store.subgraph("Acme")
    assert {n for n, d in g.nodes(data=True) if d["kind"] == "statement"} == {"s1", "s2"}
    assert g.nodes["solar panels"]["category"] == "resource optimisation"


def test_text_helpers_match_the_annotation_pipeline():
    assert clean_page("S U S T A I N A B I L I T Y\nreport") == "SUSTAINABILITY report"
    assert split_sentences("We act. We plan (e.g. solar). Done.") == [
        "We act.", "We plan (e.g. solar).", "Done."
    ]
    assert normalise("Scope 1 & 2 emissions!") == "scope 1 2 emissions"
    assert aspect_key("Our energy consumption") == "energy consumption"


def test_ingest_extracted_rejects_bad_rows(tmp_path):
    """Externally extracted spans enter as method='llm' and only if they are real substrings."""
    import json

    from graph_rag.build.aspects import ingest_extracted

    store = _fixture_store(tmp_path)
    pred = tmp_path / "pred.jsonl"
    pred.write_text(
        "\n".join(
            json.dumps(r)
            for r in [
                {"stmt_id": "s1", "spans": [{"text": "solar panels", "category": "resource optimisation"}]},
                {"stmt_id": "s2", "spans": [{"text": "wind turbines", "category": "emissions control"}]},
                {"stmt_id": "s2", "spans": [{"text": "solar panels", "category": "not a category"}]},
                {"stmt_id": "nope", "spans": [{"text": "solar panels", "category": "workplace"}]},
            ]
        ),
        encoding="utf-8",
    )
    stats = ingest_extracted(store, pred, verbose=False)
    assert stats["rejected"] == {
        "unknown_stmt_id": 1, "not_a_substring": 1, "bad_category": 1, "empty_span": 0
    }
    assert stats["llm_mentions"] == 1
    rows = store.con.execute("SELECT method, count(*) FROM mentions GROUP BY 1 ORDER BY 1").fetchall()
    assert dict(rows) == {"gold_span": 1, "string_match": 1}  # s1/solar panels already existed
