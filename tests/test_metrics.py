"""Hand-checked metric values, so a refactor cannot silently change the numbers."""

from gw_common.eval import metrics as M
from gw_common.schemas import Label

IM, P, U, N = Label.IMPLEMENTED, Label.PLANNING, Label.INDETERMINATE, Label.NONE


def test_action_metrics_ignores_none_gold():
    gold = [IM, P, U, N]
    pred = [IM, P, U, IM]
    r = M.action_metrics(gold, pred)
    assert r["n"] == 3
    assert r["accuracy"] == 1.0
    assert r["macro_f1"] == 1.0


def test_macro_f1_hand_computed():
    # gold: IM IM P ; pred: IM P P  -> IM: p=1, r=0.5, f=2/3 ; P: p=0.5, r=1, f=2/3 ; U: 0 support, f=0
    r = M.action_metrics([IM, IM, P], [IM, P, P])
    assert abs(r["per_label"]["implemented"]["f1"] - 2 / 3) < 1e-9
    assert abs(r["per_label"]["planning"]["f1"] - 2 / 3) < 1e-9
    assert abs(r["macro_f1"] - (2 / 3 + 2 / 3 + 0) / 3) < 1e-9


def test_pairdet_binary():
    r = M.pairdet_metrics([IM, N, N, P], [IM, N, P, N])
    assert (r["tp"], r["fp"], r["fn"], r["tn"]) == (1, 1, 1, 1)
    assert abs(r["f1"] - 0.5) < 1e-9


def test_flip_analysis_net():
    gold = [IM, P, U]
    base = [P, P, P]   # 1 wrong, 2 right -> wait: base[0] wrong, base[1] right, base[2] wrong
    new = [IM, U, P]    # new[0] right (fixed), new[1] wrong (broken), new[2] wrong (still)
    f = M.flip_analysis(gold, base, new)
    assert f["wrong_to_right"] == 1
    assert f["right_to_wrong"] == 1
    assert f["net"] == 0


def test_mcnemar_symmetry():
    gold = [IM, IM, IM, IM]
    a = [IM, P, IM, P]
    b = [P, IM, IM, P]
    r = M.mcnemar(gold, a, b)
    assert r["b"] == 1 and r["c"] == 1
    assert r["p_value"] == 1.0


def test_ndcg_perfect_and_empty():
    assert M.ndcg_at_k(["a", "b"], {"a", "b"}, k=2) == 1.0
    assert M.ndcg_at_k(["x"], set(), k=2) == 0.0
