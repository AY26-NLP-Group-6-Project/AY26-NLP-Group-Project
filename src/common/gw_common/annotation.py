"""Read `kb/annotation/eval.xlsx` and turn it into frozen evaluation snapshots.

`eval.xlsx` is the evaluation set in the tabular form the course brief asks for: one row per record,
`text` and `label` up front, everything else as extra columns. It is the de-identified successor of
the annotators' workbook (annotators appear as A1–A6) and is self-contained:

- the 34 aspects that annotators saw but the proposer missed are already filled in
  (`aspect_source = human_filled`; the review trail is `aspect_overrides.csv`);
- the dev/test split is a column, so the file itself says which rows may be tuned on. Pilot rows are in
  dev: all six annotators labelled them and they have been read repeatedly.

Agreement is recomputed here from the annotator columns, so every number in the report comes out of
the pipeline rather than from a spreadsheet formula.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from gw_common.datasets import EVAL_DIR, write_snapshot
from gw_common.schemas import ALL_LABELS, GoldItem, Label

REPO_ROOT = Path(__file__).resolve().parents[3]
EVAL_XLSX = REPO_ROOT / "kb" / "annotation" / "eval.xlsx"
DATASET_ID = "gw1000"
SHEET = "eval"
ANNOTATORS = ["A1", "A2", "A3", "A4", "A5", "A6"]          # pseudonymous; the mapping is not kept
LLM_SOURCES = ["claude", "deepseek", "gpt"]               # columns llm_pre_<name>
SPLITS = ("dev", "test")


def read_rows(path: Path | None = None) -> list[dict[str, Any]]:
    from openpyxl import load_workbook  # imported lazily: only snapshot building needs it

    ws = load_workbook(path or EVAL_XLSX, data_only=True, read_only=True)[SHEET]
    it = ws.iter_rows(values_only=True)
    head = [str(c).strip() if c is not None else "" for c in next(it)]
    return [row for raw in it if (row := dict(zip(head, raw, strict=False))).get("id") is not None]


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


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


def build(xlsx: Path | None = None) -> dict[str, Any]:
    """Write the human-gold snapshot plus one per LLM pre-annotator, and return a build report."""
    valid = {lab.value for lab in ALL_LABELS}
    items: list[GoldItem] = []
    human_rows: list[tuple[str, list[Label]]] = []
    llm_items: dict[str, list[GoldItem]] = {name: [] for name in LLM_SOURCES}
    seen_text: set[str] = set()

    for row in read_rows(xlsx):
        item_id = str(int(float(row["id"])))
        label, split, text = _clean(row["label"]).lower(), _clean(row["split"]), _clean(row["text"])
        if label not in valid:
            raise ValueError(f"row {item_id}: label {label!r} is not one of {sorted(valid)}")
        if split not in SPLITS:
            raise ValueError(f"row {item_id}: split {split!r} is not one of {SPLITS}")
        if text in seen_text:
            raise ValueError(f"row {item_id}: duplicate sentence; the brief forbids duplicates")
        seen_text.add(text)
        row_type = _clean(row.get("row_type"))
        human = [Label(_clean(row[c]).lower()) for c in ANNOTATORS if _clean(row.get(c))]
        if len(human) == len(ANNOTATORS):
            human_rows.append((row_type, human))
        llm_pre = {name: _clean(row.get(f"llm_pre_{name}")).lower() for name in LLM_SOURCES}
        meta = {
            "row_type": row_type,
            "aspect_source": _clean(row.get("aspect_source")),
            "aspect_weak": _clean(row.get("aspect_weak")).upper() == "Y",
            "n_annotators": len(human),
            "agreement": float(row["agreement"]) if row.get("agreement") is not None else None,
            "adjudicated": _clean(row.get("adjudicated")).upper() == "Y",
            "llm_pre": llm_pre,
        }
        common = dict(
            item_id=item_id, text=text, aspect=_clean(row.get("aspect")) or None,
            category=_clean(row.get("category")) or None, company=_clean(row["company"]),
            sgx_code=_clean(row.get("sgx_code")) or None, year=int(float(row["year"])),
            page=int(float(row["page"])) if row.get("page") is not None else None,
            file=_clean(row.get("file")) or None, context_prev=_clean(row.get("context_prev")),
            context_next=_clean(row.get("context_next")), pilot=_clean(row.get("pilot")).upper() == "Y",
            split=split, meta=meta,
        )
        items.append(GoldItem(**common, gold_label=Label(label), label_source="human_majority"))
        for name, pre in llm_pre.items():
            if pre in valid:
                llm_items[name].append(
                    GoldItem(**common, gold_label=Label(pre), label_source=f"llm_pre_{name}")
                )

    written = {"human_majority": write_snapshot(DATASET_ID, "human_majority", items, replace=True).name}
    for name, group in llm_items.items():
        written[f"llm_pre_{name}"] = write_snapshot(
            DATASET_ID, f"llm_pre_{name}", group, replace=True
        ).name

    actions = valid - {Label.NONE.value}
    report = {
        "items": len(items),
        "snapshots": written,
        "splits": dict(Counter(it.split for it in items)),
        "labels": dict(Counter(it.gold_label.value for it in items)),
        "row_types": dict(Counter(str(it.meta["row_type"]) for it in items)),
        "aspect_source": dict(Counter(str(it.meta["aspect_source"]) for it in items)),
        "action_rows_with_aspect": sum(
            it.aspect is not None and it.gold_label.value in actions for it in items
        ),
        "rows_by_annotator_count": dict(Counter(int(it.meta["n_annotators"]) for it in items)),
        "agreement": {
            "fleiss_all": fleiss_kappa([h for _, h in human_rows]),
            "fleiss_aspect": fleiss_kappa([h for t, h in human_rows if t == "aspect"]),
            "fleiss_no_aspect": fleiss_kappa([h for t, h in human_rows if t == "no_aspect"]),
        },
        "llm_pre_vs_human": {
            name: round(sum(it.meta["llm_pre"][name] == it.gold_label.value for it in items)
                        / len(items), 4)
            for name in LLM_SOURCES
        },
    }
    (EVAL_DIR / f"{DATASET_ID}.build_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def export_xls(out: Path, xlsx: Path | None = None) -> dict[str, Any]:
    """Write the legacy `.xls` the course brief names (`eval.xls`): the `eval` sheet, values only."""
    import xlwt  # optional dependency, only needed for the submission file

    rows = read_rows(xlsx)
    book = xlwt.Workbook(encoding="utf-8")
    sheet = book.add_sheet("eval")
    header = list(rows[0])
    bold = xlwt.easyxf("font: bold on")
    for c, name in enumerate(header):
        sheet.write(0, c, name, bold)
    for r, row in enumerate(rows, start=1):
        for c, name in enumerate(header):
            value = row[name]
            sheet.write(r, c, "" if value is None else value)
    out.parent.mkdir(parents=True, exist_ok=True)
    book.save(str(out))
    return {"out": str(out), "rows": len(rows), "columns": len(header)}
