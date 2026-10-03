"""The human check for RQ2: a blind sheet of promises, and the scoring of the returned sheet.

One row per promise. The annotator sees the promise as stated, what was extracted from it, and the
evidence retrieved from the deadline-year reports, and answers three questions:

1. `promise_ok`  Is this a genuine dated commitment by the company, with the deadline as extracted?
2. `fields_ok`   Are the extracted fields (metric, quantity, unit, baseline, deadline) right?
3. `outcome`     From the evidence shown, what became of it: achieved / failed / revised / unclear /
                 disappeared.

The system's proposed outcome is not on the sheet; it is kept in `promise_sheet_key.json`, so the human
judgement is independent and the proposal can be scored against it.

Sampling favours coverage over proportion: every proposed outcome class gets a floor, and no company
contributes more than a few rows, so the sheet is not thirty variations of one issuer's safety table.
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from graph_rag.config import GraphConfig
from graph_rag.promises.extract import out_dir
from graph_rag.promises.outcome import OUTCOMES

SHEET_NAME = "check"
COLUMNS = ["promise_id", "company", "stated_in", "promise_sentence", "extracted", "restated_in",
           "other_versions", "evidence", "promise_ok", "fields_ok", "outcome", "evidence_ref", "note"]
CLASS_FLOOR = 10
PER_COMPANY = 4
EVIDENCE_CHARS = 420


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def describe_target(p: dict) -> str:
    parts = [f"metric: {p['metric']}"]
    if p["quantity"] is not None:
        number = int(p["quantity"]) if float(p["quantity"]).is_integer() else p["quantity"]
        parts.append(f"{p['direction'] or 'target'}: {number}{p['unit'] or ''}")
    elif p["direction"]:
        parts.append(f"direction: {p['direction']}")
    if p["baseline_year"]:
        parts.append(f"baseline: {p['baseline_year']}")
    parts.append(f"deadline: {p['target_year']}")
    parts.append(f"kind: {p['kind']}" + (" (recurring)" if p["recurring"] else ""))
    return "\n".join(parts)


def sample(promises: list[dict], outcomes: dict[str, dict], n: int, seed: int) -> list[dict]:
    """Seeded: a floor per proposed outcome, then round-robin over classes, capped per company."""
    rng = random.Random(seed)
    by_class: dict[str, list[dict]] = defaultdict(list)
    for p in promises:
        if p["promise_id"] in outcomes:
            by_class[outcomes[p["promise_id"]]["outcome"]].append(p)
    for group in by_class.values():
        group.sort(key=lambda p: p["promise_id"])
        rng.shuffle(group)
    chosen: list[dict] = []
    per_company: Counter = Counter()

    def take(cls: str) -> bool:
        while by_class[cls]:
            p = by_class[cls].pop()
            if per_company[p["company"]] < PER_COMPANY:
                per_company[p["company"]] += 1
                chosen.append(p)
                return True
        return False

    classes = sorted(by_class, key=lambda c: len(by_class[c]))          # rare classes first
    for cls in classes:
        for _ in range(CLASS_FLOOR):
            if len(chosen) >= n or not take(cls):
                break
    while len(chosen) < n and any(by_class.values()):
        progressed = False
        for cls in classes:
            if len(chosen) < n and take(cls):
                progressed = True
        if not progressed:
            break
    rng.shuffle(chosen)
    return chosen


def export(cfg: GraphConfig, out: Path | None = None, n: int = 75, seed: int = 20261003) -> dict:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    base = out_dir(cfg)
    promises = [p for p in _load(base / "promises.jsonl") if p["checkable"]]
    outcomes = {o["promise_id"]: o for o in _load(base / "outcomes.jsonl")}
    chosen = sample(promises, outcomes, n, seed)

    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append(COLUMNS)
    key = {}
    for p in chosen:
        o = outcomes[p["promise_id"]]
        evidence = "\n\n".join(
            f"[{e['ref']}] {e['year']} report, p.{e['page']}: {e['text'][:EVIDENCE_CHARS]}"
            for e in o["evidence"]
        ) or "(nothing retrieved)"
        others = "; ".join(
            f"deadline {r['target_year']}"
            + (f", quantity {r['quantity']:g}" if r["quantity"] is not None else "")
            + f" (first stated {r['first_stated']})" for r in p["related"]
        )
        restated = ", ".join(str(y) for y in p["stated_in_years"][1:])
        ws.append([
            p["promise_id"], p["company"], f"{p['origin']['year']} report, p.{p['origin']['page']}",
            p["origin"]["text"], describe_target(p), restated, others, evidence,
            None, None, None, None, None,
        ])
        key[p["promise_id"]] = {"outcome": o["outcome"], "rationale": o["rationale"],
                                "evidence_refs": o["evidence_refs"]}
    widths = {"A": 9, "B": 16, "C": 16, "D": 60, "E": 30, "F": 12, "G": 26, "H": 95,
              "I": 11, "J": 10, "K": 14, "L": 12, "M": 34}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDE7F0")
    fill = PatternFill("solid", fgColor="FFF6D5")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        for cell in row[8:13]:
            cell.fill = fill
    last = len(chosen) + 1
    for col, formula in (("I", '"Y,N"'), ("J", '"Y,N"'), ("K", '"' + ",".join(OUTCOMES) + '"')):
        dv = DataValidation(type="list", formula1=formula, allow_blank=True)
        dv.add(f"{col}2:{col}{last}")
        ws.add_data_validation(dv)
    ws.freeze_panes = "E2"

    guide = wb.create_sheet("guide")
    for line in GUIDE:
        guide.append(line)
    guide.column_dimensions["A"].width = 18
    guide.column_dimensions["B"].width = 120
    for row in guide.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    out = out or (base / "promise_check.xlsx")
    wb.save(out)
    (base / "promise_sheet_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return {"rows": len(chosen), "companies": len({p["company"] for p in chosen}),
            "by_kind": dict(Counter(p["kind"] for p in chosen)),
            "by_target_year": dict(sorted(Counter(p["target_year"] for p in chosen).items())),
            "checkable_pool": len(promises), "out": str(out)}


GUIDE = [
    ["Promise check", "One row = one dated commitment a company made in an earlier sustainability report."],
    [],
    ["What you see", ""],
    ["stated_in", "The report (year, page) where the commitment was first found."],
    ["promise_sentence", "The statement as it appears in that report."],
    ["extracted", "What the pipeline read out of it: metric, quantity, baseline, deadline year, kind."],
    ["restated_in", "Later report years that repeat the same commitment."],
    ["other_versions", "The same company's commitments on a similar metric with a different deadline or "
                       "quantity: possible moved goalposts."],
    ["evidence", "Statements retrieved from the company's reports for the deadline year and the year "
                 "after, tagged E1, E2, ... with report year and page."],
    [],
    ["What you fill", ""],
    ["promise_ok", "Y if this is the company's own forward-looking commitment with a deadline, and the "
                   "deadline year extracted is right. N if it is a result already achieved, a national "
                   "or regulatory goal, not a commitment, or the deadline is wrong. If N, leave the rest "
                   "blank."],
    ["fields_ok", "Y if metric, quantity, unit and baseline are all right; N otherwise (say what in note)."],
    ["outcome", "Judge only from the evidence shown:"],
    ["  achieved", "The evidence says the target was met or the deliverable completed by the deadline, or "
                   "reports a figure that plainly meets it."],
    ["  failed", "The evidence says it was missed, or reports a figure at the deadline that plainly "
                 "falls short."],
    ["  revised", "The evidence restates the commitment with a later deadline, a weaker or changed quantity, "
                  "or a changed baseline, without reporting the original as met."],
    ["  unclear", "The evidence talks about this target or its metric but does not let you tell whether it "
                  "was met (progress with no verdict, 'on track')."],
    ["  disappeared", "Nothing in the evidence refers to this target or its metric."],
    ["evidence_ref", "The tag(s) your outcome rests on, e.g. E2. Leave blank for disappeared."],
    ["note", "Anything worth knowing: a wrong field, evidence that is about something else, a case worth "
             "writing up."],
    [],
    ["Be strict", "General statements that the company cares about the topic are not 'achieved'."],
    ["Recurring targets", "An annual target renewed every year ('zero incidents in FY2023') is judged "
                          "for the deadline year given. Seeing it set again for the next year is routine "
                          "renewal, not 'revised': if the deadline year's result is reported, choose "
                          "achieved or failed; if the evidence only restates it for the next year, choose "
                          "unclear. Use 'revised' only when its level or scope was changed."],
]


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    labels = sorted(set(a) | set(b))
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[lab] / n * cb[lab] / n for lab in labels)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def score(cfg: GraphConfig, sheet: Path | None = None) -> dict:
    from openpyxl import load_workbook

    base = out_dir(cfg)
    sheet = sheet or (base / "promise_check.xlsx")
    key = json.loads((base / "promise_sheet_key.json").read_text(encoding="utf-8"))
    promises = {p["promise_id"]: p for p in _load(base / "promises.jsonl")}
    ws = load_workbook(sheet, data_only=True)[SHEET_NAME]
    it = ws.iter_rows(values_only=True)
    head = [str(c) for c in next(it)]
    rows = [dict(zip(head, r, strict=False)) for r in it if r[0]]

    def yn(v) -> bool | None:
        s = str(v or "").strip().upper()
        return True if s == "Y" else False if s == "N" else None

    judged = [r for r in rows if yn(r["promise_ok"]) is not None]
    valid = [r for r in judged if yn(r["promise_ok"])]
    fields = [r for r in valid if yn(r["fields_ok"]) is not None]
    scored = [r for r in valid if str(r["outcome"] or "").strip().lower() in OUTCOMES]
    human = [str(r["outcome"]).strip().lower() for r in scored]
    system = [key[r["promise_id"]]["outcome"] for r in scored]
    pairs = list(zip(human, system, strict=True))
    confusion = {h: dict(Counter(s for hh, s in pairs if hh == h)) for h in OUTCOMES if h in human}
    per_class = {}
    for cls in OUTCOMES:
        tp = sum(h == cls and s == cls for h, s in zip(human, system, strict=True))
        fp = sum(h != cls and s == cls for h, s in zip(human, system, strict=True))
        fn = sum(h == cls and s != cls for h, s in zip(human, system, strict=True))
        if tp + fp + fn:
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            per_class[cls] = {"precision": precision, "recall": recall, "support": tp + fn}
    result = {
        "rows": len(rows),
        "judged": len(judged),
        "extraction": {
            "promise_ok": sum(yn(r["promise_ok"]) for r in judged),
            "promise_precision": sum(yn(r["promise_ok"]) for r in judged) / len(judged) if judged else None,
            "fields_ok_rate": sum(yn(r["fields_ok"]) for r in fields) / len(fields) if fields else None,
        },
        "outcome": {
            "n": len(scored),
            "human_distribution": dict(Counter(human)),
            "system_distribution": dict(Counter(system)),
            "accuracy": sum(h == s for h, s in pairs) / len(scored) if scored else None,
            "cohen_kappa": cohen_kappa(human, system),
            "per_class": per_class,
            "confusion_human_rows_system_cols": confusion,
            "human_by_kind": {
                kind: dict(Counter(h for r, h in zip(scored, human, strict=True)
                                   if promises[r["promise_id"]]["kind"] == kind))
                for kind in sorted({promises[r["promise_id"]]["kind"] for r in scored})
            },
        },
    }
    (base / "promise_check_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
