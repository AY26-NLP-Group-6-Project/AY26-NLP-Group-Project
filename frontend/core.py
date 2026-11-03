"""What the demo front end runs: one dev-split item through one registered system, step by step.

Nothing here is Streamlit. `app.py` calls these functions and times each step; the numbers in
`docs/results.md` come from the evaluation harness (`gw_common.eval`), and the demo follows the same
rules: the system never sees the gold label, the target sentence is dropped from the evidence, the shared
classifier (RQ1) or the shared judge (RQ2) reads what the system's retriever returned.
"""

from __future__ import annotations

import csv
import json
import random
import subprocess
from pathlib import Path

from gw_common import datasets, registry
from gw_common.eval import rq2 as R
from gw_common.eval.runner import EVIDENCE_K, build_query, majority_labels
from gw_common.evidence import drop_target
from gw_common.judges import promise as J
from gw_common.llm import REPO_ROOT, LLMClient, LLMSettings
from gw_common.schemas import (
    ALL_LABELS,
    EvalItem,
    EvidenceCondition,
    EvidenceSpan,
    GoldItem,
    Label,
    Prediction,
)

RQ1, RQ2 = "rq1", "rq2"
STORE_MANIFEST = REPO_ROOT / "artifacts" / "baseline" / "statements" / "manifest.json"
RESULTS_DIR = REPO_ROOT / "results"
KB_DIR = REPO_ROOT / "kb"
NO_RETRIEVAL = (EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.LOCAL)
PAGE_ZOOM = 1.4

TASKS = {
    RQ1: {
        "short": "RQ1 · label a sentence",
        "title": "RQ1 · Does retrieved evidence improve the label?",
        "labels": [lab.value for lab in ALL_LABELS],
        "k": EVIDENCE_K,
        "dataset": "gw1000 · dev 331 of 1,000 sentences (test 669, unopened)",
        "definition": """
**Task.** One sentence from an SGX-listed company's sustainability report and one candidate aspect
(for example *Scope 3 emissions*). Label what the sentence says about that aspect, on the A3CG scheme
(Ong et al., ACL 2025):

- `implemented` — an action has been taken
- `planning` — an action or a commitment is planned
- `indeterminate` — unclear whether, or how, the company engages with the aspect
- `none` — the phrase is not a sustainability aspect

**Question.** Does evidence retrieved from the company's *own* reports (the same report, or its other
years) change that label, and for the better, against the sentence-only setting?

**How it is scored.** One shared classifier reads the sentence plus at most *k* evidence spans and
answers with a label, a rationale and the sources it cites (`[T]` the sentence, `[C]` its neighbours,
`[E1]`… the evidence). Macro-F1 over the three action labels; systems are compared paired on the same
items, with repeats, because the model re-samples.
""",
    },
    RQ2: {
        "short": "RQ2 · follow a promise",
        "title": "RQ2 · What became of a dated commitment?",
        "labels": list(J.REPORTED),
        "k": R.K_WINDOW,
        "dataset": "rq2promises · dev 123 of 373 checkable promises (test 250, unopened)",
        "definition": """
**Task.** A report makes a dated commitment ("reduce Scope 1 intensity by 20 % by 2025"). What do the
company's later reports say became of it?

- `achieved` — reported as met by the deadline
- `failed` — missed, or re-dated / weakened without the original being reported as met
- `unclear` — later reports touch the target or its metric but do not settle it
- `disappeared` — the commitment is never mentioned again

**Question.** Can retrieval over the company's later reports (the *window*: from the report after the
promise up to the year after its deadline) find the statements a reader needs, so that a fixed judge
names the outcome a human annotator would?

**How it is scored.** The system's retriever returns at most *k* statements from the window. The shared
judge labels each statement (about this very target? does it state the deadline year's result? does it
move the deadline?) and a fixed rule names the outcome, defaulting to `unclear`. Accuracy, κ and
macro-F1 over the four outcomes; the share of gold-unclear promises given a verdict, the share of
settled ones left unclear, and how many verdicts are right.
""",
    },
}


# --------------------------------------------------------------------------- setup facts
def settings() -> LLMSettings:
    return LLMSettings.from_env()


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:  # noqa: BLE001 - provenance is best effort
        return "unknown"


def kb_facts() -> dict:
    """The statement store's manifest (counts, hash, embedding model), or nothing when it is not there."""
    if not STORE_MANIFEST.exists():
        return {}
    return json.loads(STORE_MANIFEST.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- the dev split
def load_items(task: str, split: str = "dev") -> list:
    """RQ1: the gold items of the split. RQ2: the gold rows (each carries its promise record)."""
    if task == RQ1:
        items, _ = datasets.load("gw1000", "human_majority")
        return [it for it in items if split == "all" or it.split == split]
    rows, _ = R.load_gold(split)
    return [r for r in rows if r["outcome"] in J.REPORTED]


def item_id(task: str, item) -> str:
    return item.item_id if task == RQ1 else item["promise_id"]


def gold_of(task: str, item) -> str | None:
    """The gold label of a dev item; a custom item has none."""
    if task == RQ1:
        return item.gold_label.value if isinstance(item, GoldItem) else None
    return item.get("outcome") if "outcome" in item else None


def pick(items: list, task: str, current: str | None = None, rng: random.Random | None = None):
    """Another item than the current one, uniformly at random."""
    rng = rng or random.Random()
    pool = [it for it in items if item_id(task, it) != current] or list(items)
    return rng.choice(pool)


def find(items: list, task: str, wanted: str):
    wanted = wanted.strip()
    return next((it for it in items if item_id(task, it) == wanted), None)


def companies(items: list, task: str) -> list[str]:
    return sorted({it.company if task == RQ1 else it["company"] for it in items})


# --------------------------------------------------------------------------- custom queries
def custom_rq1(text: str, aspect: str | None, company: str, year: int) -> EvalItem:
    return EvalItem(
        item_id="custom",
        text=text.strip(),
        aspect=(aspect or "").strip() or None,
        company=company,
        year=int(year),
    )


def custom_promise(
    company: str, sentence: str, metric: str, origin_year: int, target_year: int, recurring: bool = False
) -> dict:
    """A promise record with the fields the retrievers and the judge read; no gold, no related targets."""
    sentence = sentence.strip()
    return {
        "promise_id": "custom",
        "company": company,
        "metric": metric.strip() or sentence,
        "quantity": None,
        "unit": None,
        "direction": None,
        "baseline_year": None,
        "target_year": int(target_year),
        "kind": "qualitative",
        "recurring": bool(recurring),
        "checkable": True,
        "related": [],
        "stated_in_years": [int(origin_year)],
        "outcome_years": [int(target_year), int(target_year) + 1],
        "origin": {
            "year": int(origin_year),
            "page": None,
            "text": sentence,
            "target_text": sentence,
            "stmt_id": None,
            "file": None,
            "target_id": None,
        },
    }


def window_of(promise: dict) -> tuple[int, int]:
    """The report years a `promise_window` retriever may read."""
    return promise["origin"]["year"] + 1, promise["target_year"] + 1


# --------------------------------------------------------------------------- systems
def systems_for(task: str) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Registered systems that can take part in `task`, with the conditions they offer, and the ones
    that could not be loaded with the reason. Loading a system is cheap; its retriever is built on use."""
    ok: dict[str, list[str]] = {}
    failed: dict[str, str] = {}
    for name in sorted(registry.available()):
        try:
            conditions = [c.value for c in registry.load(name).supported_conditions()]
        except Exception as exc:  # noqa: BLE001 - a broken system is reported, not fatal
            failed[name] = f"{type(exc).__name__}: {exc}"
            continue
        if task == RQ1:
            conditions = [c for c in conditions if c != EvidenceCondition.PROMISE_WINDOW.value]
            if conditions:
                ok[name] = conditions
        elif EvidenceCondition.PROMISE_WINDOW.value in conditions:
            ok[name] = [EvidenceCondition.PROMISE_WINDOW.value]
    return ok, failed


def load_system(name: str):
    return registry.load(name)


def warm_up(system, condition: EvidenceCondition) -> None:
    """Build what the run will use, so the first-use cost lands in the load step: the retriever (unless
    the condition needs none), the classifier, and the cross-encoder's model when the retriever reranks."""
    if condition not in NO_RETRIEVAL:
        retriever = system.retriever()
        reranker = getattr(retriever, "reranker", None)
        if reranker is not None and hasattr(reranker, "rerank"):
            reranker.rerank("warm up", ["warm up"])
    if condition is not EvidenceCondition.PROMISE_WINDOW:
        system.classifier()


def embed_tokens(system) -> int:
    """Embedding tokens the system's retriever has spent so far, when it exposes an LLM client."""
    retriever = getattr(system, "_retriever", None)
    usage = getattr(getattr(retriever, "client", None), "usage", None) or {}
    return int(usage.get("embed_tokens", 0))


# --------------------------------------------------------------------------- RQ1 steps
def retrieve_rq1(system, item, condition: EvidenceCondition, k: int) -> tuple[list[EvidenceSpan], int]:
    """The evidence the classifier will see, and how many returned spans were the target sentence."""
    if condition in NO_RETRIEVAL:
        return [], 0
    retriever = system.retriever()
    if retriever is None:
        return [], 0
    query = build_query(item, condition)
    return drop_target(retriever.retrieve(query, k=k), query)


def classify_rq1(system, item, condition: EvidenceCondition, spans: list[EvidenceSpan]) -> Prediction:
    eval_item = item.to_eval_item() if isinstance(item, GoldItem) else item
    evidence = {eval_item.item_id: spans} if spans else None
    return system.classifier().classify([eval_item], condition=condition, evidence=evidence)[0]


def vote_rq1(predictions: list[Prediction]) -> Label:
    return majority_labels([[p.label] for p in predictions])[0]


# --------------------------------------------------------------------------- RQ2 steps
def retrieve_rq2(system, promise: dict, k: int) -> list[dict]:
    """The window evidence as the rows the judge reads (report order, E-tags, `follows`)."""
    return R.evidence_of(system.retriever().retrieve(R.promise_query(promise), k=k))


def judge_rq2(promise: dict, evidence: list[dict], client: LLMClient, version: str = J.DEFAULT_JUDGE) -> dict:
    return J.judge(promise, evidence, client, version)


def vote_rq2(outcomes: list[str]) -> str:
    """The judge's own rule: a strict majority, otherwise unclear; then the reported four-way label."""
    return J.reported(J.vote(outcomes))


def usage_delta(after: dict, before: dict) -> dict:
    return {
        key: int(after.get(key, 0)) - int(before.get(key, 0))
        for key in ("calls", "cache_hits", "input_tokens", "output_tokens", "embed_tokens")
    }


# --------------------------------------------------------------------------- pages and sources
def resolve_pdf(file: str | None) -> Path | None:
    """The report a span cites, when the raw corpus is on this machine: either a `raw/<company>/…pdf`
    path (the sentence set) or a report sha256 (the graph and the chunk store)."""
    if not file:
        return None
    if file.lower().endswith(".pdf"):
        path = KB_DIR / file
        return path if path.exists() else None
    hits = sorted((KB_DIR / "raw").glob(f"*/*_{file[:8]}.pdf")) if (KB_DIR / "raw").exists() else []
    return hits[0] if hits else None


def page_png(pdf: Path, page: int, zoom: float = PAGE_ZOOM) -> bytes | None:
    """One page of a report as PNG (1-based page numbers, as the corpus records them)."""
    try:
        import fitz  # pymupdf, a graph-rag dependency
    except ImportError:
        return None
    with fitz.open(pdf) as doc:
        if not 1 <= page <= doc.page_count:
            return None
        return doc[page - 1].get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")


def source_urls() -> dict[str, str]:
    """Where each report was fetched from (`kb/manifest.csv`), by sha256 and by file path."""
    path = KB_DIR / "manifest.csv"
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            url = (row.get("source_url") or "").strip()
            if url:
                out[row.get("sha256", "")] = url
                out[row.get("file", "")] = url
    return out


# --------------------------------------------------------------------------- published runs
def _store(manifest: dict) -> str:
    info = manifest.get("config", {}).get("retriever") or {}
    if info.get("store") == "graph":
        return f"graph {info.get('graph_build_id')}"
    if info.get("store"):
        return f"{info['store']} {info.get('chunks_sha256', '')}".strip()
    return "—"


def published_runs(task: str) -> list[dict]:
    """Every condition of every published run of `task` under `results/`, one row each."""
    rows = []
    for metrics_path in sorted(RESULTS_DIR.glob("*/*/metrics.json")):
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        manifest = json.loads(metrics_path.with_name("manifest.json").read_text(encoding="utf-8"))
        if (metrics.get("task") or manifest.get("task")) != task:
            continue
        for condition, block in metrics["conditions"].items():
            if block.get("status") != "ok":
                continue
            vote = block["majority"]["action"]
            speed = block.get("speed_cost", {})
            retrieval = speed.get("retrieval") or {}
            rows.append(
                {
                    "run": metrics_path.parent.relative_to(RESULTS_DIR).as_posix(),
                    "system": metrics["system"],
                    "condition": condition,
                    "items": metrics["n_items"],
                    "repeats": metrics.get("repeats", 1),
                    "vote macro-F1": round(vote["macro_f1"], 4),
                    "vote accuracy": round(vote["accuracy"], 4) if "accuracy" in vote else None,
                    "macro-F1 mean ± sd": f"{block['aggregate']['macro_f1']['mean']:.4f} ± "
                    f"{block['aggregate']['macro_f1']['sd']:.3f}",
                    "unstable items": block["aggregate"].get("unstable_items"),
                    "retrieval p50 ms": round(retrieval["p50_ms"]) if retrieval.get("p50_ms") else None,
                    "USD per 1k items": (
                        round(speed["cost_per_1k_items_usd"], 2)
                        if speed.get("cost_per_1k_items_usd") is not None
                        else None
                    ),
                    "store": _store(manifest),
                    "model": (manifest.get("llm") or {}).get("chat_model"),
                }
            )
    return rows
