"""Answer-level RAG metrics for a finished run: faithfulness, answer relevance, context precision.

The three follow RAGAS (Es et al., 2024), implemented here so that every intermediate judgement (the
statements an answer was split into, the verdict on each, the questions generated from it, the verdict on
each retrieved passage) is written to disk and can be audited.

- **Faithfulness**: the rationale is split into atomic statements; each is judged against the sources
  the classifier saw. Score = supported statements / statements.
- **Answer relevance**: questions are generated back from the answer and compared with the question
  that was actually asked, by embedding cosine. Score = mean similarity, 0 when the answer is
  noncommittal.
- **Context precision**: each retrieved passage is judged relevant or not to reaching the reference
  label; score = mean of precision@i over the relevant ranks (RAGAS). **Context relevance** is the plain
  share of relevant passages. Both exist only where something was retrieved.

Scoring is post hoc, from a run directory, so the classification run stays cheap and earlier runs can
be scored too:

    gw-eval --ragas artifacts/runs/<run_id>
    gw-eval --ragas artifacts/runs/<run_id> --ragas-export-check check.csv     # blind sheet for humans
    gw-eval --ragas artifacts/runs/<run_id> --ragas-score-check check.csv      # judge vs human agreement

The judge is an LLM and may be the model that wrote the answers. Treat its scores as provisional until
the spot-check says how often a human agrees with it.
"""

from __future__ import annotations

import csv
import json
import random
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from gw_common import datasets
from gw_common.classifiers.llm_action import CONTEXT_CHARS, EVIDENCE_CHARS
from gw_common.llm import REPO_ROOT, LLMClient
from gw_common.schemas import EvidenceCondition, GoldItem

PROMPT_PATH = REPO_ROOT / "configs" / "prompts" / "rag_judge.md"
METRICS = ("faithfulness", "answer_relevance", "context_precision", "context_relevance")
MAX_EVIDENCE = 3
_JSON_RE = re.compile(r"\{.*\}", re.S)


def _prompts(path: Path = PROMPT_PATH) -> dict[str, str]:
    parts = re.split(r"^## (\w+)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def _json(text: str) -> dict | None:
    match = _JSON_RE.search(text or "")
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except ValueError:
        return None


def question_for(item: GoldItem) -> str:
    aspect = item.aspect or "any sustainability aspect"
    return (f"What does this sentence from {item.company}'s {item.year} sustainability report say about "
            f"the company's action on '{aspect}': implemented, planning, indeterminate or none? "
            f"Sentence: {item.text}")


def sources_for(item: GoldItem, condition: str, spans: list[dict]) -> list[tuple[str, str]]:
    """The tagged sources exactly as the classifier saw them: (tag, text)."""
    out = [("T", item.text)]
    if condition == EvidenceCondition.LOCAL.value and (item.context_prev or item.context_next):
        out.append(("C", f"{item.context_prev[-CONTEXT_CHARS:]} … {item.context_next[:CONTEXT_CHARS]}"))
    for i, s in enumerate(spans[:MAX_EVIDENCE], 1):
        where = f"({s['company']}, {s['year']}, p.{s.get('page')})"
        out.append((f"E{i}", f"{where} {s['text'][:EVIDENCE_CHARS]}"))
    return out


def context_precision(relevant: list[bool]) -> float | None:
    """RAGAS: mean of precision@i over the ranks that hold a relevant passage; 0 if none is relevant."""
    if not relevant:
        return None
    hits, total = 0, 0.0
    for i, rel in enumerate(relevant, 1):
        if rel:
            hits += 1
            total += hits / i
    return total / hits if hits else 0.0


class RagJudge:
    def __init__(self, client: LLMClient | None = None, workers: int = 8) -> None:
        self.client = client or LLMClient()
        self.workers = workers
        self.prompts = _prompts()

    def _ask(self, section: str, user: str) -> dict | None:
        reply = self.client.chat(
            [{"role": "system", "content": self.prompts[section]}, {"role": "user", "content": user}],
            max_tokens=700,
        )
        return _json(reply.text)

    def faithfulness(self, label: str, rationale: str, sources: list[tuple[str, str]]) -> dict:
        if not rationale.strip():
            return {"score": None, "statements": []}
        block = "\n".join(f"[{tag}] {text}" for tag, text in sources)
        obj = self._ask("faithfulness", f"SOURCES:\n{block}\n\nLABEL: {label}\nRATIONALE: {rationale}")
        statements = [
            {"statement": str(s.get("statement", "")), "supported": bool(s.get("supported")),
             "source": str(s.get("source", "none"))}
            for s in (obj or {}).get("statements", []) if isinstance(s, dict)
        ]
        if not statements:
            return {"score": None, "statements": [], "parse_ok": obj is not None}
        return {"score": sum(s["supported"] for s in statements) / len(statements),
                "statements": statements}

    def answer_relevance(self, question: str, label: str, rationale: str) -> dict:
        if not rationale.strip():
            return {"score": None, "questions": []}
        obj = self._ask("answer_relevance", f"ANSWER: The label is {label}. {rationale}")
        questions = [str(q) for q in (obj or {}).get("questions", []) if str(q).strip()][:3]
        if not questions:
            return {"score": None, "questions": []}
        vectors = self.client.embed([question, *questions])
        sims = (vectors[1:] @ vectors[0]).tolist()
        noncommittal = bool((obj or {}).get("noncommittal"))
        return {"score": 0.0 if noncommittal else float(np.mean(sims)), "questions": questions,
                "similarities": [round(s, 4) for s in sims], "noncommittal": noncommittal}

    def context(self, item: GoldItem, sources: list[tuple[str, str]]) -> dict:
        passages = [(tag, text) for tag, text in sources if tag.startswith("E")]
        if not passages:
            return {"precision": None, "relevance": None, "verdicts": []}
        block = "\n".join(f"[{tag}] {text}" for tag, text in passages)
        obj = self._ask(
            "context_precision",
            f"ASPECT: {item.aspect or '(none given)'}\nTARGET: {item.text}\n"
            f"REFERENCE label: {item.gold_label.value}\n\nRETRIEVED PASSAGES:\n{block}",
        )
        by_ref = {str(v.get("ref", "")).strip("[] ").upper(): v
                  for v in (obj or {}).get("verdicts", []) if isinstance(v, dict)}
        if not by_ref:
            return {"precision": None, "relevance": None, "verdicts": [], "parse_ok": obj is not None}
        verdicts = [{"ref": tag, "relevant": bool(by_ref.get(tag, {}).get("relevant")),
                     "reason": str(by_ref.get(tag, {}).get("reason", ""))} for tag, _ in passages]
        flags = [v["relevant"] for v in verdicts]
        return {"precision": context_precision(flags), "relevance": sum(flags) / len(flags),
                "verdicts": verdicts}

    def score_one(self, item: GoldItem, condition: str, pred: dict, spans: list[dict]) -> dict:
        sources = sources_for(item, condition, spans)
        faith = self.faithfulness(pred["label"], pred.get("rationale", ""), sources)
        relevance = self.answer_relevance(question_for(item), pred["label"], pred.get("rationale", ""))
        ctx = self.context(item, sources)
        return {
            "condition": condition, "item_id": item.item_id,
            "label": pred["label"], "gold": item.gold_label.value,
            "correct": pred["label"] == item.gold_label.value,
            "rationale": pred.get("rationale", ""),
            "cited": [c["ref"] for c in pred.get("citations", [])],
            "sources": [{"ref": tag, "text": text} for tag, text in sources],
            "faithfulness": faith["score"], "statements": faith["statements"],
            "answer_relevance": relevance["score"], "questions": relevance.get("questions", []),
            "noncommittal": relevance.get("noncommittal", False),
            "context_precision": ctx["precision"], "context_relevance": ctx["relevance"],
            "context_verdicts": ctx["verdicts"],
        }


def _load_run(run_dir: Path, rep: int) -> tuple[dict, dict[str, dict[str, dict]], dict]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    preds: dict[str, dict[str, dict]] = defaultdict(dict)
    for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        if line:
            p = json.loads(line)
            if p.get("rep", 0) == rep:
                preds[p["condition"]][p["item_id"]] = p
    evidence: dict[tuple[str, str], list[dict]] = {}
    for line in (run_dir / "evidence.jsonl").read_text(encoding="utf-8").splitlines():
        if line:
            e = json.loads(line)
            evidence[(e["condition"], e["item_id"])] = e["spans"]
    return manifest, preds, evidence


def _mean(values: list[float | None]) -> float | None:
    kept = [v for v in values if v is not None]
    return sum(kept) / len(kept) if kept else None


def summarise(rows: list[dict]) -> dict:
    """Per-condition means, overall and split by whether the predicted label was correct."""
    out: dict[str, dict] = {}
    for condition in sorted({r["condition"] for r in rows}):
        sub = [r for r in rows if r["condition"] == condition]
        block = {"n": len(sub)}
        for metric in METRICS:
            block[metric] = _mean([r[metric] for r in sub])
            block[f"{metric}_n"] = sum(r[metric] is not None for r in sub)
        block["statements_per_answer"] = _mean([float(len(r["statements"])) for r in sub])
        block["noncommittal_rate"] = sum(r["noncommittal"] for r in sub) / len(sub)
        for flag, name in ((True, "when_correct"), (False, "when_wrong")):
            part = [r for r in sub if r["correct"] is flag]
            block[name] = {"n": len(part), "faithfulness": _mean([r["faithfulness"] for r in part]),
                           "answer_relevance": _mean([r["answer_relevance"] for r in part])}
        out[condition] = block
    return out


def score_run(
    run_dir: Path, *, conditions: list[str] | None = None, rep: int = 0, sample: int | None = None,
    seed: int = 20260930, judge: RagJudge | None = None,
) -> dict:
    manifest, preds, evidence = _load_run(run_dir, rep)
    items, _ = datasets.load(manifest["dataset_id"], manifest["label_source"])
    by_id = {it.item_id: it for it in items}
    judge = judge or RagJudge()
    jobs = []
    for condition in conditions or sorted(preds):
        ids = sorted(preds.get(condition, {}), key=int)
        if sample and sample < len(ids):
            ids = sorted(random.Random(seed).sample(ids, sample), key=int)
        jobs += [(by_id[i], condition, preds[condition][i], evidence.get((condition, i), [])) for i in ids]
    with ThreadPoolExecutor(max_workers=judge.workers) as pool:
        rows = list(pool.map(lambda job: judge.score_one(*job), jobs))

    summary = {
        "run_id": manifest["run_id"], "rep": rep, "n_scored": len(rows),
        "judge": judge.client.settings.describe(), "prompt": PROMPT_PATH.name,
        "note": "LLM-judged; see the spot-check for agreement with human judgement",
        "conditions": summarise(rows),
    }
    with (run_dir / "ragas.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (run_dir / "ragas.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (run_dir / "ragas.md").write_text(render(summary), encoding="utf-8")
    return summary


def _f(v: float | None) -> str:
    return "—" if v is None else f"{v:.3f}"


def render(summary: dict) -> str:
    judge = summary["judge"]
    lines = [f"# RAG answer-level metrics · {summary['run_id']}", "",
             f"- judge: `{judge.get('chat_model')}` (effort `{judge.get('reasoning_effort')}`), "
             f"embeddings `{judge.get('embed_model')}` · prompt `{summary['prompt']}`"
             f" · repeat {summary['rep']}",
             "- LLM-judged. Read together with the human spot-check before quoting.", "",
             "| condition | n | faithfulness | answer relevance | context precision | context relevance"
             " | statements / answer | noncommittal |",
             "|---|---|---|---|---|---|---|---|"]
    for cond, b in summary["conditions"].items():
        lines.append(f"| {cond} | {b['n']} | {_f(b['faithfulness'])} | {_f(b['answer_relevance'])} "
                     f"| {_f(b['context_precision'])} | {_f(b['context_relevance'])} "
                     f"| {_f(b['statements_per_answer'])} | {b['noncommittal_rate']:.3f} |")
    lines += ["", "## Faithfulness by whether the label was right", "",
              "| condition | correct: n / faithfulness | wrong: n / faithfulness |", "|---|---|---|"]
    for cond, b in summary["conditions"].items():
        c, w = b["when_correct"], b["when_wrong"]
        lines.append(f"| {cond} | {c['n']} / {_f(c['faithfulness'])} | {w['n']} / {_f(w['faithfulness'])} |")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- human spot-check
CHECK_COLUMNS = ["check_id", "kind", "condition", "item_id", "company", "year", "aspect", "target",
                 "sources_shown", "answer", "unit", "human_verdict", "human_note"]


def export_check(run_dir: Path, out: Path, n_answers: int = 50, seed: int = 20260930) -> dict:
    """A blind judging sheet: one row per rationale statement and per retrieved passage, for a sample
    of answers. The judge's verdicts are kept apart in `ragas_check_key.json`, so the human decides
    without seeing them. Fill `human_verdict` with Y or N."""
    rows = [json.loads(line) for line in (run_dir / "ragas.jsonl").read_text(encoding="utf-8").splitlines()
            if line]
    if not rows:
        raise ValueError("ragas.jsonl is empty: score the run first")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    items, _ = datasets.load(manifest["dataset_id"], manifest["label_source"])
    by_id = {it.item_id: it for it in items}
    rng = random.Random(seed)
    by_condition: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["statements"]:
            by_condition[r["condition"]].append(r)
    per_condition = max(1, n_answers // max(1, len(by_condition)))
    chosen = [r for cond in sorted(by_condition)
              for r in rng.sample(by_condition[cond], min(per_condition, len(by_condition[cond])))]

    sheet, key = [], {}
    for r in chosen:
        item = by_id[r["item_id"]]
        shown = "\n".join(f"[{s['ref']}] {s['text']}" for s in r["sources"])
        base = {"condition": r["condition"], "item_id": r["item_id"], "company": item.company,
                "year": item.year, "aspect": item.aspect or "", "target": item.text,
                "sources_shown": shown, "answer": f"{r['label']}: {r['rationale']}"}
        for s in r["statements"]:
            cid = f"S{len(sheet) + 1:04d}"
            sheet.append({"check_id": cid, "kind": "statement_supported", **base,
                          "unit": s["statement"], "human_verdict": "", "human_note": ""})
            key[cid] = bool(s["supported"])
        for v in r["context_verdicts"]:
            cid = f"S{len(sheet) + 1:04d}"
            text = next((s["text"] for s in r["sources"] if s["ref"] == v["ref"]), "")
            sheet.append({"check_id": cid, "kind": "passage_relevant", **base,
                          "unit": f"[{v['ref']}] {text}", "human_verdict": "", "human_note": ""})
            key[cid] = bool(v["relevant"])
    rng.shuffle(sheet)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHECK_COLUMNS)
        writer.writeheader()
        writer.writerows(sheet)
    (run_dir / "ragas_check_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    kinds = defaultdict(int)
    for row in sheet:
        kinds[row["kind"]] += 1
    return {"answers": len(chosen), "rows": len(sheet), "by_kind": dict(kinds), "out": str(out),
            "how": "statement_supported: can the statement be inferred from the sources shown? "
                   "passage_relevant: does the passage help reach the right label for the target? Y or N."}


def cohen_kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def score_check(run_dir: Path, sheet: Path) -> dict:
    """Agreement between the LLM judge and the human on the returned sheet, per kind of judgement."""
    key = json.loads((run_dir / "ragas_check_key.json").read_text(encoding="utf-8"))
    pairs: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    skipped = 0
    with sheet.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            verdict = (row.get("human_verdict") or "").strip().upper()
            if verdict not in ("Y", "N") or row["check_id"] not in key:
                skipped += 1
                continue
            pairs[row["kind"]].append((key[row["check_id"]], verdict == "Y"))
    out: dict[str, object] = {"skipped_rows": skipped}
    for kind, values in pairs.items():
        judge = [j for j, _ in values]
        human = [h for _, h in values]
        out[kind] = {
            "n": len(values),
            "agreement": sum(j == h for j, h in values) / len(values),
            "cohen_kappa": cohen_kappa(judge, human),
            "judge_yes_rate": sum(judge) / len(values),
            "human_yes_rate": sum(human) / len(values),
            "judge_yes_human_no": sum(j and not h for j, h in values),   # the lenient direction
            "judge_no_human_yes": sum(h and not j for j, h in values),
        }
    (run_dir / "ragas_check_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
