"""Aspect extraction hand-off: export work, score returned work (gate A8).

Decision D3 says aspects outside the 1,000 annotated sentences are extracted by an LLM. The
extractor is deliberately a *different model family* from the one that produced `LLM_pre`, so that
"which spans are aspects" and "what action does this aspect take" do not share a bias. Whoever runs
it, the output only enters the graph after clearing the gate in `score()`.

Reference band (A3CG Table 14, fine-tuned T5 aspect term extraction F1): 76.28 full dataset,
75.75 seen-average, 46.51 unseen-average.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

from gw_common.text import looks_like_sentence  # re-exported: the filter is shared

from graph_rag.config import REPO_ROOT, GraphConfig
from graph_rag.store.duckdb_store import DuckDBGraphStore

GOLD_SOURCE = REPO_ROOT / "kb" / "annotation" / "work" / "final_selection.jsonl"
CATEGORIES = (
    "resource optimisation",
    "waste management",
    "emissions control",
    "ecological conservation",
    "workplace",
    "outreach",
    "management",
    "business compliance",
    "worker & consumer safety compliance",
    "data and cybersecurity protection",
)

# Gate A8 (project thresholds, provisional until the first real run):
GATE = {"partial_f1": 0.60, "category_accuracy": 0.70, "no_aspect_false_positive_rate": 0.35}

# --------------------------------------------------------------------------- export
def export_input(
    cfg: GraphConfig, out_path: Path, limit: int | None = None, per_report: int | None = None,
    seed: int | None = None,
) -> dict:
    """Statements that need aspects, as JSONL for the external extractor."""
    with DuckDBGraphStore(cfg.db_path, read_only=True) as store:
        rows = store.con.execute(
            """
            SELECT s.stmt_id, s.text, s.company, s.year, s.page, s.sha256
            FROM statements s
            WHERE s.stmt_id NOT IN (SELECT stmt_id FROM mentions WHERE method = 'gold_span')
            ORDER BY s.company, s.year, s.stmt_id
            """
        ).fetchall()
    cols = ("stmt_id", "text", "company", "year", "page", "sha256")
    items = [dict(zip(cols, r, strict=True)) for r in rows]
    items = [i for i in items if looks_like_sentence(i["text"])]

    if per_report:
        rng = random.Random(seed or cfg.seed)
        by_report: dict[str, list[dict]] = {}
        for it in items:
            by_report.setdefault(it["sha256"], []).append(it)
        picked = []
        for _, group in sorted(by_report.items()):
            rng.shuffle(group)
            picked.extend(group[:per_report])
        items = sorted(picked, key=lambda i: (i["company"], i["year"], i["stmt_id"]))
    if limit:
        items = items[:limit]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps({k: it[k] for k in ("stmt_id", "text", "company", "year")},
                               ensure_ascii=False) + "\n")
    return {"statements": len(items), "path": str(out_path)}


def export_gold(out_path: Path, gold_source: Path = GOLD_SOURCE) -> dict:
    """Scoring gold: every annotated span of the 1,000 sentences, including the ones the master
    table drops (the master keeps one aspect per sentence; recall must be judged against all)."""
    if not gold_source.exists():
        raise FileNotFoundError(f"{gold_source} not found (it is git-ignored; ask for a copy)")
    n_spans = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for line in gold_source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            spans = [{"text": p["aspect"], "category": p["category"]} for p in rec["pairs"]]
            n_spans += len(spans)
            f.write(json.dumps({"stmt_id": f"eval{rec['sid']:04d}", "text": rec["sentence"],
                                "spans": spans}, ensure_ascii=False) + "\n")
    return {"sentences": 1000, "spans": n_spans, "path": str(out_path)}


# --------------------------------------------------------------------------- scoring
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def _tokens(s: str) -> set[str]:
    return set(_norm(s).split())


def _boundary_key(s: str) -> str:
    """Character-level identity up to case and whitespace runs: the span boundaries must agree."""
    return re.sub(r"\s+", " ", s).strip().lower()


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


@dataclass(slots=True)
class Match:
    gold: dict
    pred: dict
    score: float


def _match_spans(gold: list[dict], pred: list[dict], threshold: float) -> list[Match]:
    """Greedy one-to-one matching, best overlap first."""
    pairs = sorted(
        ((g, p, _overlap(g["text"], p["text"])) for g in gold for p in pred),
        key=lambda t: t[2],
        reverse=True,
    )
    used_g, used_p, out = set(), set(), []
    for g, p, sc in pairs:
        if sc < threshold or id(g) in used_g or id(p) in used_p:
            continue
        used_g.add(id(g))
        used_p.add(id(p))
        out.append(Match(g, p, sc))
    return out


def score(pred_path: Path, gold_path: Path) -> dict:
    gold_by_id = {
        json.loads(line)["stmt_id"]: json.loads(line)
        for line in gold_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    pred_by_id: dict[str, dict] = {}
    for line in pred_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            pred_by_id[rec["stmt_id"]] = rec

    missing = [k for k in gold_by_id if k not in pred_by_id]
    stats = {
        "gold_sentences": len(gold_by_id),
        "scored_sentences": len(gold_by_id) - len(missing),
        "missing_predictions": len(missing),
    }

    # boundary_exact: same characters up to case/whitespace (the strict reading of "exact").
    # token_set_exact: same token set, ignoring order and punctuation (lenient).
    # partial: token Jaccard >= 0.5 (the A8 gate metric).
    strict_not_substring = sum(
        1
        for sid, g in gold_by_id.items()
        for sp in pred_by_id.get(sid, {}).get("spans", [])
        if sp.get("text") and sp["text"] not in g["text"]
    )
    for name, threshold in (("boundary_exact", None), ("token_set_exact", 0.999), ("partial", 0.5)):
        tp = fp = fn = 0
        cat_hit = cat_total = 0
        for sid, g in gold_by_id.items():
            p = pred_by_id.get(sid, {"spans": []})
            gold_spans, pred_spans = g["spans"], p.get("spans", [])
            if threshold is None:
                gold_keys = [_boundary_key(x["text"]) for x in gold_spans]
                matches = []
                used: set[int] = set()
                for sp in pred_spans:
                    k = _boundary_key(sp.get("text", ""))
                    for gi, gk in enumerate(gold_keys):
                        if gi not in used and gk == k:
                            used.add(gi)
                            matches.append(Match(gold_spans[gi], sp, 1.0))
                            break
            else:
                matches = _match_spans(gold_spans, pred_spans, threshold)
            tp += len(matches)
            fp += len(pred_spans) - len(matches)
            fn += len(gold_spans) - len(matches)
            for m in matches:
                cat_total += 1
                cat_hit += (m.pred.get("category") or "").strip().lower() == m.gold["category"].lower()
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        stats[name] = {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}
        if name == "partial":
            stats["category_accuracy"] = cat_hit / cat_total if cat_total else 0.0
    stats["spans_not_verbatim_substring"] = strict_not_substring

    empty_gold = [sid for sid, g in gold_by_id.items() if not g["spans"]]
    invented = sum(bool(pred_by_id.get(sid, {}).get("spans")) for sid in empty_gold)
    stats["no_aspect_sentences"] = len(empty_gold)
    stats["no_aspect_false_positive_rate"] = invented / len(empty_gold) if empty_gold else 0.0

    stats["gate"] = {
        "thresholds": GATE,
        "partial_f1": stats["partial"]["f1"] >= GATE["partial_f1"],
        "category_accuracy": stats["category_accuracy"] >= GATE["category_accuracy"],
        "no_aspect_false_positive_rate": (
            stats["no_aspect_false_positive_rate"] <= GATE["no_aspect_false_positive_rate"]
        ),
    }
    stats["gate"]["passed"] = all(v for k, v in stats["gate"].items() if k != "thresholds")
    return stats
