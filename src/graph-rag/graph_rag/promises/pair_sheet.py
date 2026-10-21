"""The two-annotator check sheet for RQ2: export, blind copies, merging, scoring.

One row per promise. Two annotators fill their own five columns (promise_ok, fields_ok, outcome,
evidence_ref, note) without seeing each other's; disagreements are settled in `adjudicate` and the
settled label goes to `final`. The labels are achieved / failed / unclear / disappeared: a commitment
whose deadline passed without the target being reported as met is failed, whether the report admits
the miss or moves the date. The system's proposal is never on the sheet; it stays in the key file.

A second tab holds the annotation guide and live inter-annotator agreement (Excel formulas over the
check tab), so the people filling the sheet see the agreement as it forms. `score_pair` recomputes the
same figures in Python, scores the system against each annotator and against `final`, and weights the
sample back to the pools it was drawn from.

The sample mixes two parts, and the key records which row is which: promises already judged once on
this evidence (so the earlier labels can be re-used as Annotator 1 and the headline rows gain a second
opinion), and a plain random draw from the promises never checked, whose raw rates estimate that pool.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from graph_rag.config import GraphConfig
from graph_rag.promises import sheet as single
from graph_rag.promises.extract import out_dir
from graph_rag.promises.outcome import REPORTED, reported

SHEET_NAME = "check"
GUIDE_SHEET = "guide and IAA"
ANN_FIELDS = ("promise_ok", "fields_ok", "outcome", "evidence_ref", "note")
BASE = ["promise_id", "company", "stated_in", "promise_sentence", "extracted", "restated_in",
        "other_versions", "evidence"]
HEADER = BASE + [f"a1_{f}" for f in ANN_FIELDS] + [f"a2_{f}" for f in ANN_FIELDS] + ["adjudicate", "final"]
GROUPS = [("Promise", 1, 7), ("Evidence", 8, 8), ("Annotator 1", 9, 13), ("Annotator 2", 14, 18),
          ("Adjudication", 19, 20)]
FINAL_LABELS = (*REPORTED, "not_a_promise")
FIRST_ROW = 3                                   # two header rows: group titles, then field names
COL = {name: i + 1 for i, name in enumerate(HEADER)}
DESIGN = "_design"


def _letter(name: str) -> str:
    from openpyxl.utils import get_column_letter

    return get_column_letter(COL[name])


def export_pair(cfg: GraphConfig, out: Path, outcomes: Path, held_out: Path | None = None,
                n_random: int = 90, seed: int = 20261021, exclude: tuple[Path, ...] = (),
                prefill: bool = True) -> dict:
    """Write the master workbook.

    `held_out`: an earlier filled single-annotator sheet on the same evidence; its rows are included
    and, with `prefill`, its labels become Annotator 1 (revised → failed). `n_random` more promises are
    drawn at random from the checkable promises not on `held_out` or any `exclude` sheet.
    """
    from openpyxl import Workbook
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    def clean(value):
        return ILLEGAL_CHARACTERS_RE.sub(" ", value) if isinstance(value, str) else value

    base = out_dir(cfg)
    promises = {p["promise_id"]: p for p in single._load(base / "promises.jsonl") if p["checkable"]}
    judged = {o["promise_id"]: o for o in single._load(outcomes)}
    rng = random.Random(seed)

    held_rows, prefilled = [], {}
    held_design = {}
    if held_out:
        held_rows = [r for r in single.read_rows(held_out)]
        held_ids = [r["promise_id"] for r in held_rows]
        key_path = held_out.with_suffix(".key.json")
        held_key = json.loads(key_path.read_text(encoding="utf-8")) if key_path.exists() else {}
        held_design = {"sheet": held_out.name, "pool": held_key.get(single.POOL),
                       "drawn_as": {i: held_key[i]["outcome"] for i in held_ids if i in held_key}}
        if prefill:
            for r in held_rows:
                outcome = str(r.get("outcome") or "").strip().lower()
                prefilled[r["promise_id"]] = {
                    "promise_ok": r.get("promise_ok"), "fields_ok": r.get("fields_ok"),
                    "outcome": reported(outcome) if outcome else None,
                    "evidence_ref": r.get("evidence_ref"), "note": r.get("note")}
    seen = set(prefilled) | {r["promise_id"] for r in held_rows}
    for s in exclude:
        seen |= single.sheet_ids(Path(s))
    remaining = sorted(i for i in promises if i not in seen and i in judged)
    random_ids = sorted(rng.sample(remaining, min(n_random, len(remaining))))
    chosen = [r["promise_id"] for r in held_rows] + random_ids
    rng.shuffle(chosen)                          # so the two parts cannot be told apart on the sheet

    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append([None] * len(HEADER))
    for title, first, last in GROUPS:
        ws.cell(1, first, title)
        if last > first:
            ws.merge_cells(start_row=1, start_column=first, end_row=1, end_column=last)
    ws.append(HEADER)
    key = {}
    for pid in chosen:
        p, o = promises[pid], judged[pid]
        others = "; ".join(
            f"deadline {r['target_year']}"
            + (f", quantity {r['quantity']:g}" if r["quantity"] is not None else "")
            + f" (first stated {r['first_stated']})" for r in p["related"])
        a1 = prefilled.get(pid, {})
        ws.append([clean(v) for v in (
            pid, p["company"], f"{p['origin']['year']} report, p.{p['origin']['page']}", p["origin"]["text"],
            single.describe_target(p), ", ".join(str(y) for y in p["stated_in_years"][1:]), others,
            single.evidence_cell(o["evidence"], p["target_year"]),
            *(a1.get(f) for f in ANN_FIELDS), *([None] * len(ANN_FIELDS)), None, None,
        )])
        key[pid] = {"outcome": o["outcome"], "reported": reported(o["outcome"]), "rationale": o["rationale"],
                    "evidence_refs": o["evidence_refs"],
                    "part": "held_out" if pid in held_design.get("drawn_as", {}) else "random"}
    key[DESIGN] = {"held_out": held_design, "random": {"pool": len(remaining), "n": len(random_ids),
                                                      "seed": seed}}

    widths = {"A": 9, "B": 16, "C": 16, "D": 60, "E": 30, "F": 12, "G": 26, "H": 95}
    for name in HEADER[8:]:
        widths[_letter(name)] = 34 if name.endswith("note") or name == "adjudicate" else 12
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for cell in [*ws[1], *ws[2]]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDE7F0")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    fills = {"a1": PatternFill("solid", fgColor="FFF6D5"), "a2": PatternFill("solid", fgColor="E8F4E0"),
             "adj": PatternFill("solid", fgColor="F3E6F7")}
    for row in ws.iter_rows(min_row=FIRST_ROW):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        for cell in row[COL["a1_promise_ok"] - 1:COL["a1_note"]]:
            cell.fill = fills["a1"]
        for cell in row[COL["a2_promise_ok"] - 1:COL["a2_note"]]:
            cell.fill = fills["a2"]
        for cell in row[COL["adjudicate"] - 1:COL["final"]]:
            cell.fill = fills["adj"]
    last = FIRST_ROW + len(chosen) - 1
    labels = '"' + ",".join(REPORTED) + '"'
    for name, formula in (("a1_promise_ok", '"Y,N"'), ("a1_fields_ok", '"Y,N"'), ("a1_outcome", labels),
                          ("a2_promise_ok", '"Y,N"'), ("a2_fields_ok", '"Y,N"'), ("a2_outcome", labels),
                          ("final", '"' + ",".join(FINAL_LABELS) + '"')):
        dv = DataValidation(type="list", formula1=formula, allow_blank=True)
        dv.add(f"{_letter(name)}{FIRST_ROW}:{_letter(name)}{last}")
        ws.add_data_validation(dv)
    ws.freeze_panes = f"E{FIRST_ROW}"

    _guide_tab(wb, last)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    out.with_suffix(".key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"rows": len(chosen), "held_out": len(held_rows), "random": len(random_ids),
            "random_pool": len(remaining), "prefilled_annotator1": len(prefilled),
            "by_proposed_outcome": dict(Counter(key[i]["reported"] for i in chosen)),
            "companies": len({promises[i]["company"] for i in chosen}), "out": str(out),
            "key": str(out.with_suffix(".key.json"))}


def _guide_tab(wb, last: int) -> None:
    """The guide, then live agreement figures computed by Excel from the check tab."""
    from openpyxl.styles import Alignment, Font

    ws = wb.create_sheet(GUIDE_SHEET)
    for line in single.GUIDE:
        ws.append(line)
    ws.append([])
    ws.append(["Inter-annotator agreement", "computed live from the check tab, on rows both annotators "
                                             "have labelled; the scorer recomputes the same figures"])
    ws.cell(ws.max_row, 1).font = Font(bold=True)
    rng = lambda name: f"{SHEET_NAME}!${_letter(name)}${FIRST_ROW}:${_letter(name)}${last}"  # noqa: E731
    k1, k2 = rng("a1_outcome"), rng("a2_outcome")
    ws.append(["rows labelled by both", f'=SUMPRODUCT(({k1}<>"")*({k2}<>""))'])
    n_row = ws.max_row
    ws.append(["outcome agreements", f'=SUMPRODUCT(({k1}<>"")*({k2}<>"")*({k1}={k2}))'])
    agree_row = ws.max_row
    ws.append(["observed agreement", f'=IF(B{n_row}=0,"",B{agree_row}/B{n_row})'])
    po_row = ws.max_row
    ws.append(["label", "Annotator 1", "Annotator 2", "both"])
    first_class = ws.max_row + 1
    for label in REPORTED:
        ws.append([label, f'=COUNTIFS({k1},"{label}",{k2},"<>")', f'=COUNTIFS({k2},"{label}",{k1},"<>")',
                   f'=COUNTIFS({k1},"{label}",{k2},"{label}")'])
    last_class = ws.max_row
    ws.append(["expected agreement by chance",
               f'=IF(B{n_row}=0,"",SUMPRODUCT(B{first_class}:B{last_class},C{first_class}:C{last_class})'
               f'/(B{n_row}*B{n_row}))'])
    pe_row = ws.max_row
    ws.append(["Cohen's kappa (outcome)",
               f'=IF(OR(B{n_row}=0,B{pe_row}=1),"",(B{po_row}-B{pe_row})/(1-B{pe_row}))'])
    for field in ("promise_ok", "fields_ok"):
        f1, f2 = rng(f"a1_{field}"), rng(f"a2_{field}")
        ws.append([f"{field} agreement",
                   f'=IF(SUMPRODUCT(({f1}<>"")*({f2}<>""))=0,"",'
                   f'SUMPRODUCT(({f1}<>"")*({f2}<>"")*({f1}={f2}))/SUMPRODUCT(({f1}<>"")*({f2}<>"")))'])
    ws.append(["rows with a final label", f"=COUNTA({rng('final')})"])
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 110
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def blind_copy(master: Path, out: Path, annotator: int) -> Path:
    """The master with the other annotator's columns and the adjudication emptied, for independent work."""
    from openpyxl import load_workbook

    wb = load_workbook(master)
    ws = wb[SHEET_NAME]
    other = "a1_" if annotator == 2 else "a2_"
    for row in ws.iter_rows(min_row=FIRST_ROW):
        for name, idx in COL.items():
            if name.startswith(other) or name in ("adjudicate", "final"):
                row[idx - 1].value = None
    wb.save(out)
    return out


def merge(master: Path, filled: Path, annotator: int) -> dict:
    """Copy one annotator's five columns from a filled copy into the master, by promise id."""
    from openpyxl import load_workbook

    prefix = f"a{annotator}_"
    source = {r["promise_id"]: r for r in read_pair_rows(filled)}
    wb = load_workbook(master)
    ws = wb[SHEET_NAME]
    copied = 0
    for row in ws.iter_rows(min_row=FIRST_ROW):
        pid = row[0].value
        if pid in source:
            for field in ANN_FIELDS:
                row[COL[prefix + field] - 1].value = source[pid].get(prefix + field)
            copied += 1
    wb.save(master)
    return {"copied": copied, "annotator": annotator, "master": str(master)}


def read_pair_rows(sheet: Path) -> list[dict]:
    from openpyxl import load_workbook

    ws = load_workbook(sheet, data_only=True)[SHEET_NAME]
    rows = []
    for values in ws.iter_rows(min_row=FIRST_ROW, values_only=True):
        if values[0] and values[0] != "promise_id":
            rows.append(dict(zip(HEADER, values, strict=False)))
    return rows


def _label(value) -> str | None:
    s = str(value or "").strip().lower()
    return s if s in FINAL_LABELS else None


def score_pair(cfg: GraphConfig, sheet: Path, outcomes: Path | None = None) -> dict:
    """Agreement between the annotators, and the system against each of them and against `final`."""
    base = out_dir(cfg)
    key = json.loads(sheet.with_suffix(".key.json").read_text(encoding="utf-8"))
    design = key.get(DESIGN, {})
    system = ({o["promise_id"]: reported(o["outcome"]) for o in single._load(outcomes)} if outcomes
              else {i: v["reported"] for i, v in key.items() if i != DESIGN})
    rows = read_pair_rows(sheet)

    def human(r: dict, prefix: str) -> str | None:
        ok = str(r.get(prefix + "promise_ok") or "").strip().upper()
        if ok == "N":
            return "not_a_promise"
        return _label(r.get(prefix + "outcome"))

    a1 = {r["promise_id"]: human(r, "a1_") for r in rows}
    a2 = {r["promise_id"]: human(r, "a2_") for r in rows}
    final = {r["promise_id"]: _label(r.get("final")) for r in rows}
    both = [i for i in a1 if a1[i] and a2[i]]
    result = {"rows": len(rows), "filled": {"annotator1": sum(bool(v) for v in a1.values()),
                                           "annotator2": sum(bool(v) for v in a2.values()),
                                           "final": sum(bool(v) for v in final.values())}}
    if both:
        result["iaa"] = {
            **single.agreement([a1[i] for i in both], [a2[i] for i in both], FINAL_LABELS),
            "promise_ok_agreement": _share(rows, "promise_ok"),
            "fields_ok_agreement": _share(rows, "fields_ok"),
        }
    for name, labels in (("annotator1", a1), ("annotator2", a2), ("final", final)):
        ids = [i for i in labels if labels[i] and i in system]
        if ids:
            result[f"system_vs_{name}"] = single.agreement([labels[i] for i in ids],
                                                           [system[i] for i in ids], FINAL_LABELS)
    # what the sample says about its pools, from the final labels
    parts = {"random": [i for i in final if final[i] and key[i]["part"] == "random"],
             "held_out": [i for i in final if final[i] and key[i]["part"] == "held_out"]}
    if parts["random"]:
        result["population_random"] = _raw_shares([(final[i], system[i]) for i in parts["random"]],
                                                  design.get("random", {}).get("pool"))
    held = design.get("held_out", {})
    if parts["held_out"] and held.get("pool"):
        strata: dict[str, list[tuple[str, str]]] = {}
        for i in parts["held_out"]:
            strata.setdefault(held["drawn_as"][i], []).append((final[i], system[i]))
        result["population_held_out"] = single.population(strata, held["pool"])
    name = f"{sheet.stem}.result.json"
    (base / name).write_text(json.dumps(result, indent=2), encoding="utf-8")
    sheet.with_suffix(".result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _share(rows: list[dict], field: str) -> dict:
    pairs = [(str(r.get(f"a1_{field}") or "").strip().upper(),
              str(r.get(f"a2_{field}") or "").strip().upper()) for r in rows]
    pairs = [(x, y) for x, y in pairs if x and y]
    return single._rate(sum(x == y for x, y in pairs), len(pairs))


def _raw_shares(pairs: list[tuple[str, str]], pool: int | None, draws: int = 4000,
                seed: int = 20261021) -> dict:
    """A plain random sample: its rates estimate the pool directly; bootstrap intervals."""
    rng = random.Random(seed)
    labels = sorted({h for h, _ in pairs} | set(REPORTED))
    boots = [[rng.choice(pairs) for _ in pairs] for _ in range(draws)]

    def ci(fn) -> list:
        values = sorted(fn(b) for b in boots)
        cut = int(0.025 * len(values))
        return [values[cut], values[-cut - 1]]

    out = {"n": len(pairs), "pool": pool,
           "accuracy": {"estimate": sum(h == s for h, s in pairs) / len(pairs),
                        "ci95": ci(lambda b: sum(h == s for h, s in b) / len(b))}}
    for c in labels:
        out[f"human_share.{c}"] = {"estimate": sum(h == c for h, _ in pairs) / len(pairs),
                                   "ci95": ci(lambda b, c=c: sum(h == c for h, _ in b) / len(b))}
    return out
