"""Read `kb/annotation/annotation.xlsx` and turn it into frozen evaluation snapshots.

The workbook is the annotators' file and is never written to. Two things are layered on top here:

- **Aspect overrides** (`kb/annotation/aspect_overrides.csv`). 34 rows were shown to annotators with no
  candidate aspect, and the annotators still assigned an action, meaning they saw an aspect our
  proposer missed. The spans were reviewed on 2026-09-29 and live in that CSV, keeping the workbook
  pristine and the change auditable.
- **A frozen dev/test split.** Everything that is tuned (prompts, thresholds, retrieval settings) is
  measured on dev; test is opened once for the report. The pilot rows are forced into dev: they carry
  all six annotators, were used for the agreement analysis and have been read repeatedly.

Agreement is recomputed here from the annotator columns rather than read from the workbook's IAA
sheet, so every number in the report comes out of the pipeline.
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from gw_common.datasets import EVAL_DIR, write_snapshot
from gw_common.schemas import ALL_LABELS, GoldItem, Label

REPO_ROOT = Path(__file__).resolve().parents[3]
ANNOTATION_XLSX = REPO_ROOT / "kb" / "annotation" / "annotation.xlsx"
ASPECT_OVERRIDES = REPO_ROOT / "kb" / "annotation" / "aspect_overrides.csv"
DATASET_ID = "gw1000"
SHEET = "Master"
ANNOTATORS = ["Z. Yanhai", "H. Tingrui", "L. Yu", "L. Yuanzhi", "Z. Minghao", "P. Siddharth"]
LLM_COLUMNS = {
    "claude": "LLM_pre-Claude-Fable5.1-xHigh",
    "deepseek": "LLM_pre-Deepseek-V4.1-Flash",
    "gpt": "LLM_pre-GPT-6-Astra-xHigh",
}
DEV_FRACTION = 0.30
SPLIT_SEED = 20260929
TARGET_MARK = "⟦TARGET⟧"


def _rows(path: Path) -> list[dict[str, Any]]:
    from openpyxl import load_workbook  # imported lazily: only snapshot building needs it

    ws = load_workbook(path, data_only=True, read_only=True)[SHEET]
    it = ws.iter_rows(values_only=True)
    head = [str(c).strip() if c is not None else "" for c in next(it)]
    out = []
    for raw in it:
        row = dict(zip(head, raw, strict=False))
        if row.get("ID") is None:
            continue
        out.append(row)
    return out


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _overrides(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        out = {}
        for row in csv.DictReader(f):
            aspect = row.get("Corrected_Aspect", "").strip() or row["Proposed_Aspect"].strip()
            if not aspect:
                continue
            out[str(int(float(row["ID"])))] = {
                "aspect": aspect,
                "category": (row.get("Corrected_Category", "").strip()
                             or row.get("Category", "").strip()),
                "weak": row.get("Weak", "").strip(),
                "source": row.get("Source", "").strip(),
            }
    return out


def fleiss_kappa(rows: list[list[Label]]) -> dict[str, float]:
    """Fleiss' kappa over rows that carry the same number of ratings (>= 2)."""
    rows = [r for r in rows if len(r) >= 2]
    if not rows or len({len(r) for r in rows}) != 1:
        return {"n_rows": len(rows), "kappa": float("nan"), "observed": float("nan")}
    n = len(rows[0])
    p_i, totals = [], Counter()
    for labels in rows:
        counts = Counter(labels)
        totals.update(counts)
        p_i.append((sum(c * c for c in counts.values()) - n) / (n * (n - 1)))
    observed = sum(p_i) / len(rows)
    total = sum(totals.values())
    chance = sum((totals[lab] / total) ** 2 for lab in ALL_LABELS)
    kappa = (observed - chance) / (1 - chance) if chance < 1 else float("nan")
    return {"n_rows": len(rows), "raters": n, "observed": observed, "chance": chance, "kappa": kappa}


def _assign_splits(items: list[GoldItem], dev_fraction: float, seed: int) -> None:
    """Stratified by (row_type, gold label, category); pilot rows are pinned to dev."""
    strata: dict[tuple, list[GoldItem]] = defaultdict(list)
    for it in items:
        if it.pilot:
            it.split = "dev"
            continue
        strata[(it.meta.get("row_type"), it.gold_label.value, it.category)].append(it)
    rng = random.Random(seed)
    for _, group in sorted(strata.items(), key=lambda kv: str(kv[0])):
        group.sort(key=lambda it: int(it.item_id))
        rng.shuffle(group)
        n_dev = round(len(group) * dev_fraction)
        for i, it in enumerate(group):
            it.split = "dev" if i < n_dev else "test"


def build(
    xlsx: Path | None = None,
    overrides_csv: Path | None = None,
    dev_fraction: float = DEV_FRACTION,
    seed: int = SPLIT_SEED,
) -> dict[str, Any]:
    """Write the human-gold snapshot plus one per LLM pre-annotator, and return a build report."""
    rows = _rows(xlsx or ANNOTATION_XLSX)
    overrides = _overrides(overrides_csv or ASPECT_OVERRIDES)
    items: list[GoldItem] = []
    human_rows: list[tuple[str, list[Label]]] = []
    llm_items: dict[str, list[GoldItem]] = {name: [] for name in LLM_COLUMNS}
    unused = set(overrides)

    for row in rows:
        item_id = str(int(float(row["ID"])))
        final = _clean(row.get("Final"))
        if not final:
            continue
        context = _clean(row.get("Context"))
        prev, _, nxt = context.partition(TARGET_MARK)
        row_type = _clean(row.get("RowType"))
        aspect, category = _clean(row.get("Aspect")) or None, _clean(row.get("Category")) or None
        override = overrides.get(item_id)
        if override:
            unused.discard(item_id)
            aspect, category = override["aspect"], override["category"] or category
        human = [Label(_clean(row[c]).lower()) for c in ANNOTATORS if _clean(row.get(c))]
        if len(human) == len(ANNOTATORS):
            human_rows.append((row_type, human))
        llm_pre = {name: _clean(row.get(col)).lower() for name, col in LLM_COLUMNS.items()}
        meta = {
            "row_type": row_type,
            "aspect_source": ("human_filled" if override else
                              ("llm_proposed" if row_type == "aspect" else "none_proposed")),
            "aspect_weak": bool(override and override["weak"]),
            "n_annotators": len(human),
            "agreement": float(row["Agree"]) if row.get("Agree") is not None else None,
            "tie": _clean(row.get("Tie")) == "TIE",
            "adjudicated": bool(_clean(row.get("Adjudicated"))),
            "llm_pre": llm_pre,
            "notes": _clean(row.get("Notes")) or None,
        }
        common = dict(
            item_id=item_id, text=_clean(row["Text"]), aspect=aspect, category=category,
            company=_clean(row["Company"]), sgx_code=_clean(row.get("SGX_Code")) or None,
            year=int(float(row["Year"])), page=int(float(row["Page"])) if row.get("Page") else None,
            file=_clean(row.get("File")) or None, context_prev=prev.strip(), context_next=nxt.strip(),
            pilot=_clean(row.get("Pilot")).upper() == "Y", meta=meta,
        )
        items.append(GoldItem(**common, gold_label=Label(final.lower()), label_source="human_majority"))
        for name, label in llm_pre.items():
            if label in {lab.value for lab in ALL_LABELS}:
                llm_items[name].append(
                    GoldItem(**common, gold_label=Label(label), label_source=f"llm_pre_{name}")
                )

    if unused:
        raise ValueError(f"aspect overrides for unknown or unlabelled rows: {sorted(unused)}")
    _assign_splits(items, dev_fraction, seed)
    by_id = {it.item_id: it.split for it in items}
    for group in llm_items.values():
        for it in group:
            it.split = by_id[it.item_id]

    written = {"human_majority": write_snapshot(DATASET_ID, "human_majority", items, replace=True).name}
    for name, group in llm_items.items():
        written[f"llm_pre_{name}"] = write_snapshot(
            DATASET_ID, f"llm_pre_{name}", group, replace=True
        ).name

    action = {lab.value for lab in ALL_LABELS} - {Label.NONE.value}
    report = {
        "items": len(items),
        "snapshots": written,
        "splits": dict(Counter(it.split for it in items)),
        "labels": dict(Counter(it.gold_label.value for it in items)),
        "row_types": dict(Counter(str(it.meta["row_type"]) for it in items)),
        "aspect_source": dict(Counter(str(it.meta["aspect_source"]) for it in items)),
        "action_rows_with_aspect": sum(
            it.aspect is not None and it.gold_label.value in action for it in items
        ),
        "agreement": {
            "fleiss_all": fleiss_kappa([h for _, h in human_rows]),
            "fleiss_aspect": fleiss_kappa([h for t, h in human_rows if t == "aspect"]),
            "fleiss_no_aspect": fleiss_kappa([h for t, h in human_rows if t == "no_aspect"]),
        },
        "llm_pre_vs_human": {
            name: round(sum(it.meta["llm_pre"][name] == it.gold_label.value for it in items)
                        / len(items), 4)
            for name in LLM_COLUMNS
        },
    }
    (EVAL_DIR / f"{DATASET_ID}.build_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report
