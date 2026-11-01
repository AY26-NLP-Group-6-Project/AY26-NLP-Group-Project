"""RQ2 as a gw-eval task: gold loading, the outcome metrics, a full run with a fake system and judge,
publishing and the paired comparison."""

import json
from types import SimpleNamespace

import pytest
from gw_common import datasets
from gw_common.eval import compare as C
from gw_common.eval import rq2 as R
from gw_common.schemas import EvidenceCondition, EvidenceSpan


def _promise(pid, company, deadline=2023, recurring=False):
    return {
        "promise_id": pid,
        "company": company,
        "metric": "incidents",
        "quantity": 0.0,
        "unit": "cases",
        "direction": "maintain",
        "baseline_year": None,
        "target_year": deadline,
        "kind": "quantitative",
        "recurring": recurring,
        "checkable": True,
        "related": [],
        "stated_in_years": [2021],
        "origin": {
            "year": 2021,
            "page": 3,
            "text": f"We aim for zero incidents in FY{deadline}.",
            "target_text": f"zero incidents in FY{deadline}",
            "stmt_id": f"{pid}s",
            "file": "sha",
        },
    }


GOLD = [
    ("P1", "achieved", "human_pair"),
    ("P2", "failed", "model_pair"),
    ("P3", "unclear", "model_pair"),
    ("P4", "achieved", "model_pair"),
    ("P5", "disappeared", "human_pair"),
]


@pytest.fixture
def gold_dir(tmp_path, monkeypatch):
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    rows = [
        {
            "promise_id": pid,
            "outcome": out,
            "label_source": src,
            "split": "dev",
            "pilot": False,
            "company": "Acme",
            "promise": _promise(pid, "Acme"),
        }
        for pid, out, src in GOLD
    ]
    (eval_dir / f"{R.DATASET}.{R.LABEL_SOURCE}.abc123def456.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(datasets, "EVAL_DIR", eval_dir)
    return eval_dir


def test_outcome_metrics_and_kappa():
    gold = ["achieved", "failed", "unclear", "unclear", "achieved", "disappeared"]
    pred = ["achieved", "unclear", "unclear", "failed", "achieved", "disappeared"]
    m = R.outcome_metrics(gold, pred)
    assert m["n"] == 6 and m["accuracy"] == pytest.approx(4 / 6)
    assert m["over_commitment"] == {"k": 1, "n": 2, "share": 0.5}  # gold unclear, system failed
    assert m["under_commitment"] == {"k": 1, "n": 4, "share": 0.25}  # gold failed, system unclear
    assert m["verdict_precision"]["n"] == 4 and m["verdict_precision"]["k"] == 3
    assert m["per_class"]["achieved"]["f1"] == 1.0 and m["per_class"]["failed"]["recall"] == 0.0
    assert R.kappa(gold, gold) == 1.0 and 0 < m["cohen_kappa"] < 1
    ci = R.bootstrap(gold, pred, draws=50, seed=1)
    assert ci["accuracy"]["lo"] <= m["accuracy"] <= ci["accuracy"]["hi"]


def test_load_gold_filters_the_split(gold_dir):
    rows, digest = R.load_gold("dev")
    assert len(rows) == 5 and digest == "abc123def456" and rows[0]["promise"]["company"] == "Acme"
    assert R.load_gold("test")[0] == []


class FakeClient:
    """Labels every evidence row as this target, met: the judge then says achieved; nothing retrieved
    means disappeared."""

    def __init__(self):
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
        self.settings = SimpleNamespace(
            cost_usd=lambda i, o: (i + o) / 1e6,
            describe=lambda: {"model": "fake"},
            chat_model="fake",
            reasoning_effort="low",
        )

    def chat(self, messages, max_tokens=0, response_format=None):
        self.usage["calls"] += 1
        self.usage["input_tokens"] += 100
        self.usage["output_tokens"] += 20
        refs = [
            line.split("]")[0].strip("[")
            for line in messages[1]["content"].splitlines()
            if line.startswith("[E")
        ]
        body = {
            "annual": False,
            "outcome": "achieved",
            "rationale": "met",
            "evidence": [
                {"ref": r, "relation": "this_target", "deadline_result": "met", "change": "none"}
                for r in refs
            ],
        }
        return SimpleNamespace(text=json.dumps(body))


class FakeRetriever:
    def retrieve(self, query, *, k=10):
        assert (
            query.condition is EvidenceCondition.PROMISE_WINDOW and query.meta["promise"]["company"] == "Acme"
        )
        if query.meta["promise"]["promise_id"] == "P5":
            return []  # nothing in the window: disappeared
        return [
            EvidenceSpan(
                statement_id=f"r2023p0004s00{i}",
                text=f"Statement {i} in FY2023.",
                company="Acme",
                year=2023,
                page=4,
                file="sha2023",
                why="fake",
            )
            for i in range(min(k, 2))
        ]

    def describe(self):
        return {"store": "fake"}


def test_run_rq2_writes_a_run_the_index_and_compare_can_read(gold_dir, tmp_path, monkeypatch):
    system = SimpleNamespace(
        name="fake-rag",
        supported_conditions=lambda: [EvidenceCondition.PROMISE_WINDOW],
        retriever=lambda: FakeRetriever(),
    )
    monkeypatch.setattr(R, "load_system", lambda name: system)
    run_dir = R.run_rq2(
        "fake-rag", split="dev", repeats=2, k=5, out_root=tmp_path / "runs", client=FakeClient()
    )
    assert {p.name for p in run_dir.iterdir()} == {
        "manifest.json",
        "metrics.json",
        "predictions.jsonl",
        "evidence.jsonl",
        "report.md",
    }
    preds = [
        json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(preds) == 5 * 2 and {p["condition"] for p in preds} == {"promise_window"}
    labels = {p["item_id"]: p["label"] for p in preds if p["rep"] == 0}
    assert labels["P1"] == "achieved" and labels["P5"] == "disappeared"
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    block = metrics["conditions"]["promise_window"]
    assert block["majority"]["action"]["n"] == 5 and block["majority"]["action"]["accuracy"] == pytest.approx(
        3 / 5
    )
    assert block["aggregate"]["unstable_items"] == 0 and block["evidence"]["coverage"] == pytest.approx(4 / 5)
    assert block["speed_cost"]["judge_calls_per_item"] == pytest.approx(4 / 5)  # P5 needed no call
    assert set(block["majority"]["by_source"]) == {"human_pair", "model_pair"}
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["task"] == "rq2" and manifest["dataset_hash"] == "abc123def456"
    assert manifest["config"]["judge"]["judge"] == "v2" and manifest["config"]["retriever"] == {
        "store": "fake"
    }
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "vote accuracy" in report and "verdicts that are right" in report

    results = tmp_path / "results"
    C.publish(run_dir, results, "a fake rq2 run", name="fake/rq2")
    index = (results / "README.md").read_text(encoding="utf-8")
    assert "| fake-rag | judge-v2 | `fake` | dev | 5 | 2 | abc123def456 | promise_window |" in index
    table = C.compare(run_dir, run_dir)
    assert "| promise_window | promise_window | 5 |" in table and "| 1.000 |" in table

    # the same evidence judged again: no retrieval, and the manifest says where it came from
    system.retriever = lambda: pytest.fail("nothing is to be retrieved")
    again = R.run_rq2("fake-rag", split="dev", repeats=1, k=5, out_root=tmp_path / "again",
                      client=FakeClient(), evidence_file=run_dir / "evidence.jsonl")
    manifest = json.loads((again / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["config"]["retriever"] == {"evidence_from": run_dir.name}
    metrics = json.loads((again / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["conditions"]["promise_window"]["evidence"]["coverage"] == pytest.approx(4 / 5)
