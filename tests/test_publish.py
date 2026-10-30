"""Publishing a run: a named folder under its group, and an index that reads nested folders."""

import json

from gw_common.eval.compare import publish, published_runs, write_index


def _fake_run(tmp_path, run_id, system, style, score):
    run = tmp_path / "runs" / run_id
    run.mkdir(parents=True)
    retriever = ({"store": "graph", "graph_build_id": "dev"} if system == "graph-rag"
                 else {"store": "statements", "chunks_sha256": "d8a62bfe40c6"})
    (run / "manifest.json").write_text(json.dumps({
        "run_id": run_id, "system": system, "n_items": 3, "repeats": 3, "dataset_hash": "abc123",
        "config": {"split": "dev", "classifier": {"style": style}, "retriever": retriever},
    }), encoding="utf-8")
    (run / "metrics.json").write_text(json.dumps({"conditions": {
        "sentence_only": {"status": "ok", "majority": {"action": {"macro_f1": 0.5}}},
        "cross_year_rrf": {"status": "ok", "majority": {"action": {"macro_f1": score}}},
    }}), encoding="utf-8")
    (run / "report.md").write_text("# report\n", encoding="utf-8")
    (run / "predictions.jsonl").write_text("{}\n", encoding="utf-8")       # stays local
    return run


def test_publish_names_the_folder_and_indexes_groups(tmp_path):
    results = tmp_path / "results"
    a = _fake_run(tmp_path, "20260930T083207Z-baseline-rag-rq1", "baseline-rag", "cited", 0.78)
    b = _fake_run(tmp_path, "20261002T053125Z-graph-rag-rq1", "graph-rag", "cited", 0.77)
    out = publish(a, results, "the reference baseline", name="baseline/sentence-hybrid-cited")
    assert out == results / "baseline" / "sentence-hybrid-cited"
    assert (out / "NOTE.md").read_text(encoding="utf-8") == "the reference baseline\n"
    assert (out / "metrics.json").exists() and not (out / "predictions.jsonl").exists()
    publish(b, results, "graph arms", name="graph/graph-arms-cited")
    assert [p.relative_to(results).as_posix() for p in published_runs(results)] == [
        "baseline/sentence-hybrid-cited", "graph/graph-arms-cited"]

    index = write_index(results).read_text(encoding="utf-8")
    link = "[baseline/sentence-hybrid-cited](baseline/sentence-hybrid-cited/report.md)"
    assert f"| {link} | baseline-rag | cited | `statements` d8a62bfe40c6 | dev " in index
    assert "| graph-rag | cited | graph `dev` | dev " in index
    assert "| 0.7800 | the reference baseline | `20260930T083207Z-baseline-rag-rq1` |" in index
    assert "| cross_year_rrf | 0.7700 | graph arms | `20261002T053125Z-graph-rag-rq1` |" in index

    # a run published without a name keeps its run id as the folder, and is still indexed
    c = _fake_run(tmp_path, "20260912T030747Z-majority-rq1", "majority", "label", 0.2)
    publish(c, results)
    assert (results / "20260912T030747Z-majority-rq1" / "manifest.json").exists()
    assert len(published_runs(results)) == 3
