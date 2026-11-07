"""The three decisions scored separately, hand-checked on small cases (docs/evaluation.md section 7)."""

import json

from gw_common.eval import stages as S


def _by(levels):
    return {lv["level"]: lv for lv in levels}


def test_rq1_levels_count_a_vote_that_left_earlier_as_wrong():
    gold = ["implemented", "planning", "indeterminate", "none"]
    pred = ["implemented", "none", "indeterminate", "none"]
    r = _by(S.cascade(gold, pred, S.RQ1_LEVELS))
    assert (r["presence"]["n"], r["decidability"]["n"], r["direction"]["n"]) == (4, 3, 2)
    assert r["presence"]["accuracy"] == 0.75  # the planning sentence read as none
    assert abs(r["decidability"]["accuracy"] - 2 / 3) < 1e-9 and r["decidability"]["left"] == 1
    # direction: implemented right; the planning row's vote left at presence, so wrong and a miss
    assert r["direction"]["accuracy"] == 0.5 and r["direction"]["left"] == 1
    assert abs(r["direction"]["macro_f1"] - 0.5) < 1e-9  # implemented F1 1, planning F1 0


def test_rq2_levels_follow_the_judge_order():
    gold = ["achieved", "failed", "unclear", "disappeared"]
    pred = ["achieved", "unclear", "unclear", "unclear"]
    r = _by(S.cascade(gold, pred, S.RQ2_LEVELS))
    assert r["presence"]["n"] == 4 and r["presence"]["accuracy"] == 0.75  # the dropped one not seen
    assert r["decidability"]["n"] == 3 and abs(r["decidability"]["accuracy"] - 2 / 3) < 1e-9
    assert r["decidability"]["left"] == 0  # unclear is a class at this level, not a dropout
    assert r["direction"]["n"] == 2 and r["direction"]["accuracy"] == 0.5
    assert r["direction"]["left"] == 1


def test_perfect_votes_score_one_everywhere():
    gold = ["implemented", "planning", "indeterminate", "none", "planning"]
    for lv in S.cascade(gold, list(gold), S.RQ1_LEVELS):
        assert lv["accuracy"] == 1.0 and lv["macro_f1"] == 1.0 and lv["left"] == 0


def test_resolve_follows_a_published_folder_to_its_local_run(tmp_path):
    runs = tmp_path / "runs"
    local = runs / "20260101T000000Z-x-rq1"
    local.mkdir(parents=True)
    (local / "predictions.jsonl").write_text("", encoding="utf-8")
    published = tmp_path / "results" / "x"
    published.mkdir(parents=True)
    (published / "manifest.json").write_text(json.dumps({"run_id": local.name}), encoding="utf-8")
    assert S.resolve(published, runs) == local
    assert S.resolve(local, runs) == local


def test_score_run_votes_like_the_judge(tmp_path):
    # P00006 is a gold achieved test promise, P00024 a gold unclear one (data/eval/rq2promises.*)
    run = tmp_path / "20260101T000000Z-x-rq2"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({"run_id": run.name, "task": "rq2"}), encoding="utf-8")
    reps = {"P00006": ["achieved", "achieved", "failed"], "P00024": ["unclear", "achieved", "failed"]}
    with (run / "predictions.jsonl").open("w", encoding="utf-8") as fp:
        for pid, labels in reps.items():
            for rep, label in enumerate(labels):
                fp.write(json.dumps({"condition": "promise_window", "rep": rep, "item_id": pid,
                                     "label": label}) + "\n")
    r = _by(S.score_run(run)["conditions"]["promise_window"])
    # achieved by majority; no strict majority on the other -> unclear, which is its gold
    assert (r["presence"]["n"], r["decidability"]["n"], r["direction"]["n"]) == (2, 2, 1)
    assert r["presence"]["accuracy"] == r["decidability"]["accuracy"] == r["direction"]["accuracy"] == 1.0
    assert "P00006" in S.report_md([S.score_run(run)]) or run.name in S.report_md([S.score_run(run)])
