"""Canonicalisation: CESI metric definitions, morph normalisation, HAC blocking, gold validation."""

import json

import numpy as np
import pytest
from graph_rag.canonical.cluster import Phrase, hac_clusters, representative
from graph_rag.canonical.evaluate import cesi_metrics
from graph_rag.canonical.goldset import evaluate_against_gold, load_gold
from graph_rag.canonical.normalise import morph_key


def test_cesi_figure2_worked_example():
    """CESI (WWW 2018) Figure 2 / section 7.2: P_macro = R_macro = 2/3, P_micro = R_micro = 6/7,
    P_pair = 4/6, R_pair = 4/7."""
    predicted = [{"America", "USA", "NY4"}, {"NY1", "NY2", "NY3"}, {"California"}]
    gold = [{"America", "USA"}, {"NY1", "NY2", "NY3", "NY4"}, {"California"}]
    m = cesi_metrics(predicted, gold)
    assert m["macro"]["precision"] == pytest.approx(2 / 3)
    assert m["macro"]["recall"] == pytest.approx(2 / 3)
    assert m["micro"]["precision"] == pytest.approx(6 / 7)
    assert m["micro"]["recall"] == pytest.approx(6 / 7)
    assert m["pairwise"]["precision"] == pytest.approx(4 / 6)
    assert m["pairwise"]["recall"] == pytest.approx(4 / 7)


@pytest.mark.parametrize(
    ("surface", "key"),
    [
        ("greenhouse gas (GHG) emissions", "greenhouse gas emission"),
        ("GHG emissions", "greenhouse gas emission"),
        ("Our OH&S policies", "occupational health and safety policy"),
        ("the Group's anti-corruption policies", "anti corruption policy"),
        ("net-zero targets", "net zero target"),
        ("business ethics", "business ethics"),
        ("processes", "process"),
    ],
)
def test_morph_key(surface, key):
    assert morph_key(surface) == key


def test_hac_never_merges_across_categories():
    phrases = [Phrase("water use", "resource optimisation"), Phrase("water use", "waste management"),
               Phrase("water consumption", "resource optimisation")]
    v = np.array([[1.0, 0.0], [1.0, 0.0], [0.99, 0.141]], dtype=np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    clusters = sorted(sorted(c) for c in hac_clusters(phrases, v, similarity_threshold=0.9))
    assert clusters == [[0, 2], [1]]
    assert representative([0, 2], phrases, v) in (0, 2)


def test_gold_must_partition_each_pool(tmp_path):
    pools = tmp_path / "pools.jsonl"
    pools.write_text(json.dumps({"pool_id": "pool001", "split": "val", "category": "x",
                                 "forms": [{"form_id": "a"}, {"form_id": "b"}, {"form_id": "c"}]}),
                     encoding="utf-8")
    good = tmp_path / "good.jsonl"
    good.write_text(json.dumps({"pool_id": "pool001", "groups": [["a", "b"], ["c"]]}), encoding="utf-8")
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"pool_id": "pool001", "groups": [["a", "b"]]}), encoding="utf-8")

    gold = load_gold(pools, good)
    with pytest.raises(ValueError):
        load_gold(pools, bad)

    perfect = evaluate_against_gold({"a": "k1", "b": "k1", "c": "k2"}, gold, "val")
    assert perfect["pairwise"]["f1"] == 1.0 and perfect["macro"]["f1"] == 1.0
    split_all = evaluate_against_gold({"a": "k1", "b": "k2", "c": "k3"}, gold, "val")
    assert split_all["pairwise"]["recall"] == 0.0
    assert split_all["micro"]["precision"] == 1.0   # singletons are pure, which is why purity alone misleads


def test_verdict_clustering_never_crosses_a_rejection():
    from graph_rag.canonical.verify import Verdict, cluster_from_verdicts, parse_yes_no

    v = [
        Verdict(0, 1, 0.95, True, "Yes", False, 0, 0),
        Verdict(1, 2, 0.90, True, "Yes", False, 0, 0),
        Verdict(0, 2, 0.80, False, "No", False, 0, 0),   # A~B, B~C accepted, but A vs C rejected
        Verdict(3, 4, 0.85, True, "Yes", False, 0, 0),
    ]
    clusters = sorted(cluster_from_verdicts(5, v))
    assert [0, 1] in clusters and [2] in clusters and [3, 4] in clusters
    assert parse_yes_no("Yes.") and parse_yes_no(" yes") and not parse_yes_no("No") and not parse_yes_no("Maybe yes")


def test_candidate_pairs_respect_floor_and_groups():
    from graph_rag.canonical.verify import candidate_pairs

    v = np.array([[1, 0], [0.99, 0.141], [0, 1], [0.1, 0.995]], dtype=np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    pairs = candidate_pairs(v, [[0, 1], [2, 3]], k=5, floor=0.9)
    assert {(c.a, c.b) for c in pairs} == {(0, 1), (2, 3)}
    assert candidate_pairs(v, [[0, 2]], k=5, floor=0.9) == []
