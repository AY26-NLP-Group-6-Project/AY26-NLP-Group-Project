"""Gold outcomes for the 374 checkable promises, and their dev/test split.

Two sources, one sheet format. The group double-annotated 137 promises on the pair sheet (two
annotators, adjudicated `final`). The rest are labelled by model annotators run as sub-agents under the
same guide, two per promise, blind to each other and to the system's output, with disagreements
settled by a third pass; the annotators are calibrated first on a held-out slice of the human rows, and
that agreement is reported next to the human–human agreement. The frozen snapshot records, per promise,
the final label, who produced it and the split.

Why model annotators read the same cells as people: the sheet's evidence (`sheet.evidence_cell`) is the
trajectory evidence with each statement cut at 420 characters; judging from anything richer would make
the model labels incomparable with the human ones.

Split as for RQ1 (`data/eval/gw1000.*`): about a third dev, the rest test, stratified; the promises the
judge prompt was tuned on (the round-1 sheet) are pinned to dev, as the pilot rows were.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from graph_rag.config import GraphConfig
from graph_rag.promises import sheet as single
from graph_rag.promises.extract import out_dir
from graph_rag.promises.outcome import REPORTED, reported
from graph_rag.promises.pair_sheet import LABELS, pair_guide

DEV_SHARE = 0.331  # gw1000: 331 of 1,000
DATASET = "rq2promises"
SOURCES = ("human_pair", "model_pair")
ANNOTATORS = ("a1", "a2")


# --------------------------------------------------------------------------- what an annotator sees
def cells(p: dict, o: dict) -> dict:
    """The eight columns of the pair sheet for one promise, from the promise and its judged evidence."""
    others = "; ".join(
        f"deadline {r['target_year']}"
        + (f", quantity {r['quantity']:g}" if r["quantity"] is not None else "")
        + f" (first stated {r['first_stated']})"
        for r in p["related"]
    )
    return {
        "promise_id": p["promise_id"],
        "company": p["company"],
        "stated_in": f"{p['origin']['year']} report, p.{p['origin']['page']}",
        "promise_sentence": p["origin"]["text"],
        "extracted": single.describe_target(p),
        "restated_in": ", ".join(str(y) for y in p["stated_in_years"][1:]),
        "other_versions": others,
        "evidence": single.evidence_cell(o["evidence"], p["target_year"]),
        "deadline": p["target_year"],
    }


def packets(cfg: GraphConfig, outcomes: Path) -> dict[str, dict]:
    """Every checkable promise with judged evidence, keyed by id."""
    base = out_dir(cfg)
    promises = {p["promise_id"]: p for p in single._load(base / "promises.jsonl") if p["checkable"]}
    judged = {o["promise_id"]: o for o in single._load(outcomes)}
    return {pid: cells(promises[pid], judged[pid]) for pid in sorted(promises) if pid in judged}


def render(c: dict, label: dict | None = None) -> str:
    """One promise as the annotator reads it; with `label`, the settled outcome and the notes."""
    lines = [
        f"### {c['promise_id']} — {c['company']}",
        f"- stated in: {c['stated_in']}",
        f"- promise: {c['promise_sentence']}",
        f"- extracted: {c['extracted'].replace(chr(10), '; ')}",
        f"- restated in: {c['restated_in'] or '—'}",
        f"- other versions of this target: {c['other_versions'] or '—'}",
        "- evidence:",
        "",
        c["evidence"],
        "",
    ]
    if label:
        lines.append(f"- **final outcome: {label['final']}**")
        notes = [
            f"annotator {n[-1]}: {label[n + '_outcome']} — {label.get(n + '_note') or ''}".strip(" —")
            for n in ANNOTATORS
            if label.get(n + "_outcome")
        ]
        lines.append("- notes: " + " | ".join(notes))
        lines.append("")
    return "\n".join(lines)


def brief() -> str:
    """The annotation brief: the pair sheet's guide, then the output contract."""
    out = [
        "# Promise check: annotation brief",
        "",
        "You are one of two independent annotators. Label each promise from the evidence shown and nothing "
        "else: no outside knowledge of the company, no guess about what a company of this kind usually does. "
        "You do not see the other annotator's labels or the system's proposal.",
        "",
    ]
    for row in pair_guide():
        if not row or not row[0]:
            continue
        label, text = row[0], row[1] if len(row) > 1 else ""
        if label in ("adjudicate", "final", "Independence"):
            continue  # the adjudication columns and the sheet mechanics are not theirs
        if label == "Promise check":
            text = "One row = one dated commitment a company made in an earlier sustainability report."
        if not text:
            out += ["", f"## {label}", ""]
        elif label.startswith("  "):
            out.append(f"- **{label.strip()}**: {text}")
        else:
            out += [f"**{label}**: {text}", ""]
    out += [
        "",
        "## Boundaries the group settled",
        "",
        "Three places where the first calibration round drifted from the group's labels; follow the group.",
        "",
        "- **unclear, not disappeared**, when the evidence from the deadline year or later speaks of the "
        "subject of the target (the system, project, activity or metric area) without settling the target: "
        "a ticketing system described but no satisfaction rating recorded, sludge waste discussed but no "
        "sludge-drying project named. `disappeared` is for evidence that touches none of it.",
        "- **achieved for a practice that is shown running.** A commitment to track, monitor, report, "
        "maintain or operate something is met when the deadline-year evidence shows that practice in "
        "operation (occurrences tracked and reported to the board, training delivered, the system in use). "
        "No sentence has to say 'target met'. A figure or a general statement of concern is still not enough "
        "for a quantitative target.",
        "- **unclear when it may not be the same target.** If the extracted fields omit a qualifier that "
        "the evidence attaches to the target (a baseline, intensity rather than absolute, a named "
        "certification or scope) and you cannot tell whether the evidence speaks of this commitment or a "
        "neighbouring one, do not read a 'not achieved' or a figure as this target's verdict: choose "
        "unclear and say in the note what the mismatch is.",
        "",
        "## Output",
        "",
        "For every promise in your batch write one JSON object per line, in batch order, to the file named "
        "in your instructions:",
        "",
        '    {"promise_id": "P00145", "outcome": "achieved", "note": "E3: FY2023 figure under the cap"}',
        "",
        f"`outcome` is one of {', '.join(LABELS)}. `note` names the evidence tags the outcome rests on and, "
        "in one clause, why; if an extracted field is wrong or the evidence is about another target, say so. "
        "Label every promise; never skip one, never add one. Decide each promise on its own evidence; the "
        "reference examples show how the group applied the guide, not what share of each label to expect.",
    ]
    return "\n".join(out)


# --------------------------------------------------------------------------- the group's sheet
def read_group_sheet(path: Path) -> list[dict]:
    """Rows of the pair sheet whatever the sheet is called: the header row starts with `promise_id`."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    for ws in wb.worksheets:
        head, rows = None, []
        for values in ws.iter_rows(values_only=True):
            if head is None:
                if values and values[0] == "promise_id":
                    head = [str(c) if c is not None else "" for c in values]
                continue
            if values and values[0]:
                row = {h: v for h, v in zip(head, values, strict=False) if h}
                for k in ("a1_outcome", "a2_outcome", "final"):
                    row[k] = _label(row.get(k))
                for k in ("a1_note", "a2_note", "adjudicate"):
                    row[k] = str(row[k]).strip() if row.get(k) is not None else None
                rows.append(row)
        if rows:
            return rows
    raise ValueError(f"no sheet in {path} has a header row starting with promise_id")


def _label(value) -> str | None:
    text = str(value).strip().lower() if value is not None else ""
    return text if text in LABELS else None


def human_rows(path: Path) -> list[dict]:
    """The rows both annotators labelled and that carry a final label."""
    return [r for r in read_group_sheet(path) if r["final"] and r["a1_outcome"] and r["a2_outcome"]]


# --------------------------------------------------------------------------- rounds for the model annotators
def stratified(ids_by_class: dict[str, list[str]], n: int, seed: int, floor: int = 4) -> list[str]:
    """`n` ids, each class at least `floor` (or all it has), the rest in proportion."""
    rng = random.Random(seed)
    pools = {c: sorted(v) for c, v in ids_by_class.items() if v}
    for v in pools.values():
        rng.shuffle(v)
    total = sum(len(v) for v in pools.values())
    chosen = []
    for c, v in pools.items():
        take = min(len(v), max(floor, round(n * len(v) / total)))
        chosen += v[:take]
        pools[c] = v[take:]
    while len(chosen) > n:
        biggest = max(pools, key=lambda c: sum(1 for i in chosen if i in ids_by_class[c]))
        chosen.remove(next(i for i in reversed(chosen) if i in ids_by_class[biggest]))
    rest = [i for c in sorted(pools) for i in pools[c]]
    rng.shuffle(rest)
    chosen += rest[: max(0, n - len(chosen))]
    rng.shuffle(chosen)
    return chosen


def choose_references(rows: list[dict], exclude: set[str], per_class: int, seed: int) -> list[dict]:
    """Human rows to show as worked examples: per final class, disagreements first (their notes carry the
    reasoning), then agreed rows, never a row the annotators will be tested on."""
    rng = random.Random(seed)
    by_class: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["promise_id"] not in exclude:
            by_class[r["final"]].append(r)
    chosen = []
    for cls in sorted(by_class):
        group = by_class[cls]
        rng.shuffle(group)
        group.sort(key=lambda r: r["a1_outcome"] == r["a2_outcome"])  # disagreements first
        chosen += group[:per_class]
    rng.shuffle(chosen)
    return chosen


def write_round(
    root: Path,
    name: str,
    ids: list[str],
    all_cells: dict[str, dict],
    references: list[dict],
    batch_size: int = 10,
) -> dict:
    """Lay out one round: brief.md, references.md, batches/NN.md, and index.json naming them."""
    base = root / name
    (base / "batches").mkdir(parents=True, exist_ok=True)
    (base / "labels").mkdir(exist_ok=True)
    (base / "brief.md").write_text(brief(), encoding="utf-8")
    ref_text = [
        "# Reference examples: how the group labelled",
        "",
        "Each example shows the row as the annotators saw it, the settled outcome and both annotators' "
        "notes. Where the two disagreed, the final is the adjudicated one.",
        "",
    ]
    for r in references:
        ref_text.append(render(all_cells[r["promise_id"]], r))
    (base / "references.md").write_text("\n".join(ref_text), encoding="utf-8")
    batches = []
    for n, start in enumerate(range(0, len(ids), batch_size), 1):
        chunk = ids[start : start + batch_size]
        text = [
            f"# Batch {n:02d}: {len(chunk)} promises",
            "",
            "Label every promise below; output one JSON line per promise, in this order.",
            "",
        ]
        text += [render(all_cells[pid]) for pid in chunk]
        path = base / "batches" / f"{n:02d}.md"
        path.write_text("\n".join(text), encoding="utf-8")
        batches.append({"batch": f"{n:02d}", "file": str(path), "ids": chunk})
    index = {
        "round": name,
        "ids": ids,
        "references": [r["promise_id"] for r in references],
        "batches": batches,
        "brief": str(base / "brief.md"),
        "references_file": str(base / "references.md"),
        "labels_dir": str(base / "labels"),
    }
    (base / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    return index


def collect(labels_dir: Path, annotators: tuple[str, ...] = ANNOTATORS) -> dict[str, dict[str, dict]]:
    """Labels written by the annotators: `NN.a1.jsonl` / `NN.a2.jsonl` → {annotator: {promise_id: row}}."""
    out: dict[str, dict[str, dict]] = {a: {} for a in annotators}
    if not labels_dir.exists():
        return out
    for path in sorted(labels_dir.glob("*.jsonl")):
        annotator = path.stem.split(".")[-1]
        if annotator not in out:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip().strip(",")
            if not line or line.startswith("```"):
                continue
            row = json.loads(line)
            outcome = _label(row.get("outcome"))
            if outcome is None:
                raise ValueError(f"{path.name}: {row.get('promise_id')} has outcome {row.get('outcome')!r}")
            out[annotator][str(row["promise_id"])] = {"outcome": outcome, "note": str(row.get("note") or "")}
    return out


def against_human(labels: dict[str, dict[str, dict]], rows: list[dict]) -> dict:
    """Each model annotator, and their agreement, against the human final on the rows both have."""
    final = {r["promise_id"]: r["final"] for r in rows}
    report: dict = {}
    for a in ANNOTATORS:
        ids = [i for i in final if i in labels[a]]
        if ids:
            report[a] = single.agreement(
                [final[i] for i in ids], [labels[a][i]["outcome"] for i in ids], LABELS
            )
    both = [i for i in final if i in labels["a1"] and i in labels["a2"]]
    if both:
        report["a1_vs_a2"] = single.agreement(
            [labels["a1"][i]["outcome"] for i in both], [labels["a2"][i]["outcome"] for i in both], LABELS
        )
        agreed = [i for i in both if labels["a1"][i]["outcome"] == labels["a2"][i]["outcome"]]
        report["agreed_vs_human"] = single.agreement(
            [final[i] for i in agreed], [labels["a1"][i]["outcome"] for i in agreed], LABELS
        )
        report["disagreements"] = [
            {
                "promise_id": i,
                "human": final[i],
                "a1": labels["a1"][i]["outcome"],
                "a2": labels["a2"][i]["outcome"],
                "a1_note": labels["a1"][i]["note"],
                "a2_note": labels["a2"][i]["note"],
            }
            for i in both
            if not (labels["a1"][i]["outcome"] == labels["a2"][i]["outcome"] == final[i])
        ]
    human_pairs = [(r["a1_outcome"], r["a2_outcome"]) for r in rows]
    report["human_a1_vs_a2"] = single.agreement(
        [a for a, _ in human_pairs], [b for _, b in human_pairs], LABELS
    )
    return report


# --------------------------------------------------------------------------- the gold file
def assemble(
    human: list[dict],
    model: dict[str, dict[str, dict]],
    adjudicated: dict[str, dict],
    pilot: set[str],
    seed: int = 20261030,
) -> tuple[list[dict], list[dict]]:
    """One item per promise: the human final where the group labelled it, else the model pair's agreed
    label or the adjudicated one. Rows settled as `not_a_promise` are an extraction error, not an
    outcome, and the judge has no such label: they are returned apart and stay out of the gold file and
    the split. Then the split."""
    items = []
    for r in human:
        items.append(
            {
                "promise_id": r["promise_id"],
                "outcome": r["final"],
                "label_source": "human_pair",
                "a1": r["a1_outcome"],
                "a2": r["a2_outcome"],
                "a1_note": r.get("a1_note"),
                "a2_note": r.get("a2_note"),
                "adjudicate": r.get("adjudicate"),
                "agreed": r["a1_outcome"] == r["a2_outcome"],
            }
        )
    human_ids = {r["promise_id"] for r in human}
    for pid in sorted(set(model["a1"]) | set(model["a2"])):
        if pid in human_ids:
            continue
        a1, a2 = model["a1"].get(pid), model["a2"].get(pid)
        if a1 is None or a2 is None:
            raise ValueError(f"{pid}: only one model annotator labelled it")
        if a1["outcome"] == a2["outcome"]:
            final, adj = a1["outcome"], None
        else:
            if pid not in adjudicated:
                raise ValueError(f"{pid}: the annotators disagree and no adjudication was recorded")
            final, adj = adjudicated[pid]["outcome"], adjudicated[pid].get("note")
        items.append(
            {
                "promise_id": pid,
                "outcome": final,
                "label_source": "model_pair",
                "a1": a1["outcome"],
                "a2": a2["outcome"],
                "a1_note": a1["note"],
                "a2_note": a2["note"],
                "adjudicate": adj,
                "agreed": a1["outcome"] == a2["outcome"],
            }
        )
    excluded = sorted((i for i in items if i["outcome"] == "not_a_promise"), key=lambda i: i["promise_id"])
    items = [i for i in items if i["outcome"] != "not_a_promise"]
    assign_split(items, pilot, seed)
    return sorted(items, key=lambda i: i["promise_id"]), excluded


def assign_split(items: list[dict], pilot: set[str], seed: int, dev_share: float = DEV_SHARE) -> None:
    """Pilot promises to dev; the rest stratified by (outcome, label source) so that dev holds about
    `dev_share` of all items, as gw1000 does."""
    rng = random.Random(seed)
    for it in items:
        it["pilot"] = it["promise_id"] in pilot
        it["split"] = "dev" if it["pilot"] else None
    want_dev = round(dev_share * len(items))
    need = max(0, want_dev - sum(1 for it in items if it["split"] == "dev"))
    free = [it for it in items if it["split"] is None]
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for it in free:
        strata[(it["outcome"], it["label_source"])].append(it)
    quota = {}
    for key, group in strata.items():
        group.sort(key=lambda i: i["promise_id"])
        rng.shuffle(group)
        quota[key] = need * len(group) / len(free) if free else 0
    taken = 0
    for key, group in sorted(strata.items(), key=lambda kv: -len(kv[1])):
        k = min(len(group), round(quota[key]))
        for it in group[:k]:
            it["split"] = "dev"
        taken += k
    leftovers = [it for it in free if it["split"] is None]
    rng.shuffle(leftovers)
    for it in leftovers[: max(0, need - taken)]:
        it["split"] = "dev"
    for it in items:
        if it["split"] is None:
            it["split"] = "test"


def write_snapshot(items: list[dict], promises_path: Path, eval_dir: Path, source: str = "pair_gold") -> dict:
    """`data/eval/rq2promises.<source>.<hash>.jsonl`, hash over the frozen content, plus a build report."""
    promises = {p["promise_id"]: p for p in single._load(promises_path)}
    rows = []
    for it in items:
        p = promises[it["promise_id"]]
        rows.append(
            {
                **it,
                "promise": p,
                "company": p["company"],
                "metric": p["metric"],
                "deadline": p["target_year"],
                "origin_year": p["origin"]["year"],
                "origin_page": p["origin"]["page"],
                "promise_sentence": p["origin"]["text"],
            }
        )
    text = "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    eval_dir.mkdir(parents=True, exist_ok=True)
    path = eval_dir / f"{DATASET}.{source}.{digest}.jsonl"
    path.write_text(text, encoding="utf-8")
    report = {
        "items": len(rows),
        "snapshot": path.name,
        "splits": dict(Counter(r["split"] for r in rows)),
        "labels": dict(Counter(r["outcome"] for r in rows)),
        "label_source": dict(Counter(r["label_source"] for r in rows)),
        "labels_by_split": {
            s: dict(Counter(r["outcome"] for r in rows if r["split"] == s)) for s in ("dev", "test")
        },
        "source_by_split": {
            s: dict(Counter(r["label_source"] for r in rows if r["split"] == s)) for s in ("dev", "test")
        },
        "pilot": sum(r["pilot"] for r in rows),
        "annotators_agreed": {
            src: sum(1 for r in rows if r["label_source"] == src and r["agreed"]) for src in SOURCES
        },
        "companies": len({r["company"] for r in rows}),
    }
    (eval_dir / f"{DATASET}.build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


ADJUDICATOR = "adj"


def write_adjudication(
    root: Path,
    name: str,
    all_cells: dict[str, dict],
    labels: dict[str, dict[str, dict]],
    batch_size: int = 10,
) -> dict:
    """Batches for a third pass over the promises the two model annotators labelled differently: each row
    with both labels and notes; the adjudicator writes `NN.adj.jsonl` into `adjudication/labels/`."""
    base = root / name / "adjudication"
    (base / "batches").mkdir(parents=True, exist_ok=True)
    (base / "labels").mkdir(exist_ok=True)
    ids = sorted(
        i
        for i in labels["a1"]
        if i in labels["a2"] and labels["a1"][i]["outcome"] != labels["a2"][i]["outcome"]
    )
    batches = []
    for n, start in enumerate(range(0, len(ids), batch_size), 1):
        chunk = ids[start : start + batch_size]
        text = [
            f"# Adjudication batch {n:02d}: {len(chunk)} promises",
            "",
            "Two annotators labelled each promise below differently. Read the evidence and both notes, "
            "decide which reading follows the guide (or neither), and output one JSON line per promise, in "
            "this order, with your settled outcome and a note that says why in one clause.",
            "",
        ]
        for pid in chunk:
            text.append(render(all_cells[pid]))
            for a in ANNOTATORS:
                text.append(f"- annotator {a}: **{labels[a][pid]['outcome']}** — {labels[a][pid]['note']}")
            text.append("")
        path = base / "batches" / f"{n:02d}.md"
        path.write_text("\n".join(text), encoding="utf-8")
        batches.append({"batch": f"{n:02d}", "file": str(path), "ids": chunk})
    index = {"round": name, "ids": ids, "batches": batches, "labels_dir": str(base / "labels")}
    (base / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    return index


def build(
    group_sheet: Path,
    rounds_dir: Path,
    round_name: str,
    promises_path: Path,
    pilot_key: Path | None,
    eval_dir: Path,
) -> dict:
    """The gold file from the group's sheet and the main round's labels and adjudications."""
    human = human_rows(group_sheet)
    model = collect(rounds_dir / round_name / "labels")
    adjudicated = collect(rounds_dir / round_name / "adjudication" / "labels", (ADJUDICATOR,))[ADJUDICATOR]
    pilot = set()
    if pilot_key and pilot_key.exists():
        pilot = {k for k in json.loads(pilot_key.read_text(encoding="utf-8")) if not k.startswith("_")}
    items, excluded = assemble(human, model, adjudicated, pilot)
    report = write_snapshot(items, promises_path, eval_dir)
    report["not_a_promise_excluded"] = [
        {"promise_id": i["promise_id"], "label_source": i["label_source"],
         "note": i.get("adjudicate") or i["a1_note"]}
        for i in excluded
    ]
    report["calibration"] = {}
    for score in sorted(rounds_dir.glob("calibration*/score.json")):
        s = json.loads(score.read_text(encoding="utf-8"))
        report["calibration"][score.parent.name] = {
            k: {"n": s[k]["n"], "accuracy": round(s[k]["accuracy"], 3), "cohen_kappa": s[k]["cohen_kappa"]}
            for k in ("a1", "a2", "a1_vs_a2", "agreed_vs_human", "human_a1_vs_a2")
            if k in s
        }
    report["model_pair_adjudicated"] = sum(
        1 for i in items if i["label_source"] == "model_pair" and not i["agreed"]
    )
    (eval_dir / f"{DATASET}.build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def score_system(snapshot: Path, outcomes: Path, split: str = "dev") -> dict:
    """The judge's reported outcome against the gold on one split: dev while anything is tuned, test once.
    `not_a_promise` rows are left out (the judge has no such label)."""
    gold = [json.loads(line) for line in snapshot.read_text(encoding="utf-8").splitlines() if line]
    judged = {o["promise_id"]: reported(o["outcome"]) for o in single._load(outcomes)}
    rows = [g for g in gold if g["split"] == split and g["promise_id"] in judged]
    scored = [g for g in rows if g["outcome"] in REPORTED]
    human = [g["outcome"] for g in scored]
    system = [judged[g["promise_id"]] for g in scored]
    report = {
        "split": split,
        "snapshot": snapshot.name,
        "outcomes": outcomes.name,
        "n": len(scored),
        "not_a_promise_left_out": len(rows) - len(scored),
        **single.agreement(human, system, REPORTED),
    }
    unclear = [(h, s) for h, s in zip(human, system, strict=True) if h == "unclear"]
    verdicts = [(h, s) for h, s in zip(human, system, strict=True) if h != "unclear"]
    said = [(h, s) for h, s in zip(human, system, strict=True) if s != "unclear"]
    report["over_commitment"] = _share(sum(s != "unclear" for _, s in unclear), len(unclear))
    report["under_commitment"] = _share(sum(s == "unclear" for _, s in verdicts), len(verdicts))
    report["verdict_precision"] = _share(sum(h == s for h, s in said), len(said))
    report["by_source"] = {}
    for src in SOURCES:
        part = [(g["outcome"], judged[g["promise_id"]]) for g in scored if g["label_source"] == src]
        if part:
            report["by_source"][src] = single.agreement([h for h, _ in part], [s for _, s in part], REPORTED)
    return report


def _share(k: int, n: int) -> dict:
    return {"k": k, "n": n, "share": round(k / n, 3) if n else None}


__all__ = [
    "REPORTED",
    "cells",
    "packets",
    "render",
    "brief",
    "read_group_sheet",
    "human_rows",
    "stratified",
    "choose_references",
    "write_round",
    "collect",
    "against_human",
    "assemble",
    "assign_split",
    "write_snapshot",
]
