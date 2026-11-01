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
from graph_rag.promises.evidence import where
from graph_rag.promises.extract import out_dir
from graph_rag.promises.outcome import OUTCOMES, REPORTED, reported

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


def evidence_cell(evidence: list[dict], deadline: int) -> str:
    """The evidence as the annotator reads it: one block per report year, the deadline year marked."""
    if not evidence:
        return "(nothing retrieved)"
    lines, year = [], None
    for e in evidence:
        if e["year"] != year:
            year = e["year"]
            when = "deadline year" if year == deadline else "before the deadline" if year < deadline \
                else "after the deadline"
            lines.append(f"—— {year} report ({when}) ——")
        lines.append(f"[{e['ref']}] {where(e)}: {e['text'][:EVIDENCE_CHARS]}")
    return "\n\n".join(lines)


def read_rows(sheet: Path) -> list[dict]:
    """Rows of a check sheet as dicts, whatever header rows precede the one that starts `promise_id`."""
    from openpyxl import load_workbook

    ws = load_workbook(sheet, data_only=True)[SHEET_NAME]
    head: list[str] | None = None
    rows = []
    for values in ws.iter_rows(values_only=True):
        if head is None:
            if values and values[0] == "promise_id":
                head = [str(c) for c in values]
            continue
        if values[0]:
            rows.append(dict(zip(head, values, strict=False)))
    return rows


def sheet_ids(sheet: Path) -> set[str]:
    return {str(r["promise_id"]) for r in read_rows(sheet)}


def export(cfg: GraphConfig, out: Path | None = None, n: int = 75, seed: int = 20261003,
           outcomes: Path | None = None, exclude: tuple[Path, ...] = ()) -> dict:
    """`outcomes` is the judge output to stratify on and take the evidence from; `exclude` lists earlier
    sheets whose promises must not be drawn again, so a later round is held out from the rows a judge was
    tuned on."""
    from openpyxl import Workbook
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    def clean(value):                      # parsed PDF text can carry control characters Excel refuses
        return ILLEGAL_CHARACTERS_RE.sub(" ", value) if isinstance(value, str) else value

    base = out_dir(cfg)
    seen = set().union(*(sheet_ids(Path(s)) for s in exclude)) if exclude else set()
    promises = [p for p in _load(base / "promises.jsonl") if p["checkable"] and p["promise_id"] not in seen]
    outcomes = {o["promise_id"]: o for o in _load(Path(outcomes) if outcomes else base / "outcomes.jsonl")}
    chosen = sample(promises, outcomes, n, seed)

    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append(COLUMNS)
    key = {}
    for p in chosen:
        o = outcomes[p["promise_id"]]
        evidence = evidence_cell(o["evidence"], p["target_year"])
        others = "; ".join(
            f"deadline {r['target_year']}"
            + (f", quantity {r['quantity']:g}" if r["quantity"] is not None else "")
            + f" (first stated {r['first_stated']})" for r in p["related"]
        )
        restated = ", ".join(str(y) for y in p["stated_in_years"][1:])
        ws.append([clean(v) for v in (
            p["promise_id"], p["company"], f"{p['origin']['year']} report, p.{p['origin']['page']}",
            p["origin"]["text"], describe_target(p), restated, others, evidence,
            None, None, None, None, None,
        )])
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
    for col, formula in (("I", '"Y,N"'), ("J", '"Y,N"'), ("K", '"' + ",".join(REPORTED) + '"')):
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

    key_path = out.with_suffix(".key.json") if out else base / "promise_sheet_key.json"
    out = out or (base / "promise_check.xlsx")
    wb.save(out)
    drawn = dict(Counter(key[p["promise_id"]]["outcome"] for p in chosen))
    # the strata the rows were drawn from, so scoring can weight the sheet back to its pool
    key[POOL] = dict(Counter(outcomes[p["promise_id"]]["outcome"]
                             for p in promises if p["promise_id"] in outcomes))
    key_path.write_text(json.dumps(key, indent=1), encoding="utf-8")
    return {"rows": len(chosen), "companies": len({p["company"] for p in chosen}),
            "by_kind": dict(Counter(p["kind"] for p in chosen)),
            "by_target_year": dict(sorted(Counter(p["target_year"] for p in chosen).items())),
            "by_proposed_outcome": drawn, "pool_by_proposed_outcome": key[POOL],
            "checkable_pool": len(promises), "excluded": len(seen), "out": str(out), "key": str(key_path)}


GUIDE = [
    ["Promise check", "One row = one dated commitment a company made in an earlier sustainability report. "
                      "Two annotators label independently; where their outcomes differ the row is settled "
                      "in 'adjudicate' and the settled label goes to 'final'."],
    [],
    ["What you see", ""],
    ["stated_in", "The report (year, page) where the commitment was first found."],
    ["promise_sentence", "The statement as it appears in that report."],
    ["extracted", "What the pipeline read out of it: metric, quantity, baseline, deadline year, kind."],
    ["restated_in", "Later report years that repeat the same commitment."],
    ["other_versions", "The same company's commitments on a similar metric with a different deadline or "
                       "quantity: possible moved goalposts."],
    ["evidence", "Statements retrieved from the company's later reports, in report order, tagged E1, E2, "
                 "... with report year and page. They come from every report after the one that made the "
                 "promise, up to the year after the deadline; the deadline year's block is marked. "
                 "'directly follows E3' means the statement comes right after E3 in the report: one "
                 "passage, or one row of a table (a target cell and then its result), to be read together."],
    [],
    ["What you fill", ""],
    ["promise_ok", "Y if this is the company's own forward-looking commitment with a deadline, and the "
                   "deadline year extracted is right. N if it is a result already achieved, a national "
                   "or regulatory goal, not a commitment, or the deadline is wrong. If N, leave the rest "
                   "blank."],
    ["fields_ok", "Y if metric, quantity, unit and baseline are all right; N otherwise (say what in note)."],
    ["outcome", "Judge only from the evidence shown, for the deadline year the promise names:"],
    ["  achieved", "The evidence says the target was met or the deliverable completed in or by the "
                   "deadline year, or reports a figure that plainly meets it. A deliverable reported as "
                   "finished before the deadline counts."],
    ["  failed", "The deadline year has passed and the evidence does not report the target as met: it "
                 "says it was missed, reports a figure at the deadline that falls short, or gives the same "
                 "commitment a later date, a weaker level or a new baseline, or says it was postponed. A "
                 "moved deadline is a failed deadline."],
    ["  unclear", "The evidence from the deadline year or later talks about this target or its metric "
                  "but does not let you tell whether it was met: progress with no verdict, 'on track', a "
                  "result for part of the commitment, a result for another year."],
    ["  disappeared", "Nothing in the evidence from the deadline year or later refers to this target or "
                      "its metric. A restatement in an earlier year does not count: the question is "
                      "whether the company still speaks of it once the deadline has come."],
    ["evidence_ref", "The tag(s) your outcome rests on, e.g. E2; E5. Leave blank for disappeared."],
    ["note", "Anything worth knowing: a wrong field, evidence that is about something else, a case worth "
             "writing up."],
    ["adjudicate", "After both annotators are done, for rows where the outcomes differ: who settled it "
                   "and why, in a few words."],
    ["final", "The settled outcome, or the agreed one; not_a_promise when promise_ok is N."],
    [],
    ["Be strict", "General statements that the company cares about the topic are not 'achieved'. Do not "
                  "infer: an action reported in a later year does not show that the deadline was missed, "
                  "and a related measure (an absolute amount for an intensity target, another site, "
                  "another product) is not this target."],
    ["Annual targets", "An annual target ('zero incidents in FY2023') is judged on the result reported "
                       "for its own year: achieved if met, failed if missed. Seeing it set again for the "
                       "next year tells nothing by itself: with no result for the deadline year, choose "
                       "unclear."],
    ["Tables", "A table is parsed into fragments. A fragment that only names the target ('An accident "
               "frequency rate of zero') is not a result; the result is usually the fragment marked "
               "'directly follows'. In one long flattened row the columns run together (target, result, "
               "next year's target): if you cannot tell which column a phrase is in, do not rely on it."],
    ["Independence", "Fill your own columns without looking at the other annotator's. The system's "
                     "proposal is not on this sheet."],
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


VERDICTS = tuple(o for o in OUTCOMES if o != "unclear")
POOL = "_pool"                      # in a sheet's key: how many promises each stratum was drawn from


def agreement(human: list[str], system: list[str], classes: tuple[str, ...]) -> dict:
    """Accuracy, kappa, per-class precision and recall, and the confusion, over one set of classes."""
    pairs = list(zip(human, system, strict=True))
    per_class = {}
    for cls in classes:
        tp = sum(h == cls and s == cls for h, s in pairs)
        fp = sum(h != cls and s == cls for h, s in pairs)
        fn = sum(h == cls and s != cls for h, s in pairs)
        if tp + fp + fn:
            per_class[cls] = {"precision": tp / (tp + fp) if tp + fp else 0.0,
                              "recall": tp / (tp + fn) if tp + fn else 0.0, "support": tp + fn}
    return {
        "n": len(pairs),
        "human_distribution": dict(Counter(human)),
        "system_distribution": dict(Counter(system)),
        "accuracy": sum(h == s for h, s in pairs) / len(pairs) if pairs else None,
        "cohen_kappa": cohen_kappa(human, system),
        "per_class": per_class,
        "confusion_human_rows_system_cols": {
            h: dict(Counter(s for hh, s in pairs if hh == h)) for h in classes if h in human},
    }


def population(strata: dict[str, list[tuple[str, str]]], pool: dict[str, int],
               draws: int = 4000, seed: int = 20261003) -> dict:
    """Estimates for the promises a sheet was drawn from, not for the sheet.

    A sheet is stratified on the outcome proposed when it was drawn, with rare outcomes over-sampled, so
    its raw rates describe no population. Here each stratum's (human, system) pairs are weighted by the
    stratum's size in the pool. Intervals are 95 % bootstrap, resampling within strata. `accuracy` is on
    the reported classes (failed and revised as one, not met); `accuracy_five_way` keeps them apart.
    """
    strata = {s: pairs for s, pairs in strata.items() if pairs and pool.get(s)}
    total = sum(pool[s] for s in strata)

    def mean(sample: dict, hit) -> float:
        return sum(pool[s] / total * sum(hit(h, y) for h, y in pairs) / len(pairs)
                   for s, pairs in sample.items())

    def ratio(sample: dict, hit, among) -> float | None:
        base = mean(sample, among)
        return mean(sample, lambda h, y: among(h, y) and hit(h, y)) / base if base else None

    labels = sorted({reported(h) for pairs in strata.values() for h, _ in pairs})
    measures = {
        "accuracy": lambda s: mean(s, lambda h, y: reported(h) == reported(y)),
        "accuracy_five_way": lambda s: mean(s, lambda h, y: h == y),
        "over_commitment": lambda s: ratio(s, lambda h, y: y in VERDICTS, lambda h, y: h == "unclear"),
        "under_commitment": lambda s: ratio(s, lambda h, y: y == "unclear", lambda h, y: h in VERDICTS),
        "verdict_precision": lambda s: ratio(s, lambda h, y: h == y, lambda h, y: y in VERDICTS),
        **{f"human_share.{c}": (lambda s, c=c: mean(s, lambda h, y: reported(h) == c)) for c in labels},
    }
    rng = random.Random(seed)
    resampled = [{s: [rng.choice(pairs) for _ in pairs] for s, pairs in strata.items()} for _ in range(draws)]
    out = {"pool": total, "strata": {s: {"pool": pool[s], "sampled": len(p)} for s, p in strata.items()}}
    for name, measure in measures.items():
        values = sorted(v for v in (measure(b) for b in resampled) if v is not None)
        cut = int(0.025 * len(values))
        low, high = (values[cut], values[-cut - 1]) if values else (None, None)
        out[name] = {"estimate": measure(strata), "ci95": [low, high]}
    return out


def score(cfg: GraphConfig, sheet: Path | None = None, outcomes: Path | None = None) -> dict:
    """Score the system's outcomes against a filled sheet.

    The system side is the key written when the sheet was drawn (next to the sheet, else in the build
    directory), or, with `outcomes`, any judge's output over the same promises. The latter is only
    meaningful when that judge saw the evidence the annotator saw.

    When the key records the strata the sheet was drawn from, the result carries `population`: the
    same measures weighted back to the pool, which is what may be compared across sheets.
    """
    base = out_dir(cfg)
    sheet = sheet or (base / "promise_check.xlsx")
    beside = sheet.with_suffix(".key.json")
    key_path = beside if beside.exists() else base / "promise_sheet_key.json"
    design = json.loads(key_path.read_text(encoding="utf-8")) if key_path.exists() else {}
    key = {o["promise_id"]: o for o in _load(Path(outcomes))} if outcomes else design
    promises = {p["promise_id"]: p for p in _load(base / "promises.jsonl")}
    rows = read_rows(sheet)

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
    result = {
        "rows": len(rows),
        "judged": len(judged),
        "extraction": {
            "promise_ok": sum(yn(r["promise_ok"]) for r in judged),
            "promise_precision": sum(yn(r["promise_ok"]) for r in judged) / len(judged) if judged else None,
            "fields_ok_rate": sum(yn(r["fields_ok"]) for r in fields) / len(fields) if fields else None,
        },
        # what is reported: failed and revised as one class, not met
        "reported": agreement([reported(h) for h in human], [reported(s) for s in system], REPORTED),
        # the five-way labels as given, kept as detail
        "outcome": {
            **agreement(human, system, OUTCOMES),
            # the two ways of being wrong about how much the evidence settles
            "over_commitment": _rate(sum(h == "unclear" and s in VERDICTS for h, s in pairs),
                                     human.count("unclear")),
            "under_commitment": _rate(sum(h in VERDICTS and s == "unclear" for h, s in pairs),
                                      sum(h in VERDICTS for h in human)),
            "verdict_precision": _rate(sum(h == s and s in VERDICTS for h, s in pairs),
                                       sum(s in VERDICTS for s in system)),
            "human_by_kind": {
                kind: dict(Counter(h for r, h in zip(scored, human, strict=True)
                                   if promises[r["promise_id"]]["kind"] == kind))
                for kind in sorted({promises[r["promise_id"]]["kind"] for r in scored})
            },
        },
    }
    if design.get(POOL):
        strata: dict[str, list[tuple[str, str]]] = {}
        for r in judged:                           # a row that is no promise is a miss for any system
            label = str(r["outcome"] or "").strip().lower() if yn(r["promise_ok"]) else "not_a_promise"
            if label in OUTCOMES or label == "not_a_promise":
                drawn_as = design[r["promise_id"]]["outcome"]
                strata.setdefault(drawn_as, []).append((label, key[r["promise_id"]]["outcome"]))
        result["population"] = population(strata, design[POOL])
    name = f"promise_check_result.{Path(outcomes).stem}.json" if outcomes else "promise_check_result.json"
    (base / name).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": k / n if n else None}
