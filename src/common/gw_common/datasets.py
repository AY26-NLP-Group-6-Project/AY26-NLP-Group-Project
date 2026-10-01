"""Frozen evaluation snapshots.

A run may only use a snapshot that exists on disk with its content hash in the filename, so a
metrics file can always be traced back to exact inputs. Build one with `gw-data build gw1000`.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from gw_common.schemas import GoldItem, Label

REPO_ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = REPO_ROOT / "data" / "eval"
MASTER_CSV = REPO_ROOT / "kb" / "annotation" / "GW_master_1000.csv"
A3CG_DIR = REPO_ROOT / "tmp" / "data" / "a3cg"  # keanepotato/a3cg_greenwash release, git-ignored

# Snapshots whose items, labels and split are identical and differ only in metadata (see the experiment
# log, section 4l): runs recorded against either hash may be compared item by item.
EQUIVALENT_SNAPSHOTS = {"23dc51f1d9de": "3e18cc14e648"}


def canonical_hash(digest: str) -> str:
    return EQUIVALENT_SNAPSHOTS.get(digest, digest)


LABEL_SOURCES = ("human_majority", "llm_pre", "llm_pre_claude", "llm_pre_deepseek", "llm_pre_gpt",
                 "a3cg_gold")
# A3CG test files -> dataset ids. Seen/unseen follow the paper's three category folds.
A3CG_SPLITS = {
    "a3cg-full-test": "full/full_test.json",
    **{
        f"a3cg-f{k}-{s}-test": f"fold_{k}/fold_{k}_{s}_test.json"
        for k in (1, 2, 3)
        for s in ("seen", "unseen")
    },
}


def _hash_items(items: list[GoldItem]) -> str:
    h = hashlib.sha256()
    for it in items:
        h.update(it.model_dump_json().encode("utf-8"))
    return h.hexdigest()[:12]


def _read_master(path: Path, label_source: str) -> list[GoldItem]:
    column = "LLM_pre" if label_source == "llm_pre" else "Final"
    items: list[GoldItem] = []
    skipped = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            raw = (row.get(column) or "").strip()
            if not raw:
                skipped += 1  # human labels not adjudicated yet
                continue
            items.append(
                GoldItem(
                    item_id=str(row["ID"]),
                    text=row["Text"],
                    aspect=row["Aspect"] or None,
                    category=row["Category"] or None,
                    company=row["Company"],
                    sgx_code=row.get("SGX_Code") or None,
                    year=int(row["Year"]),
                    page=int(row["Page"]) if row.get("Page") else None,
                    file=row.get("File") or None,
                    context_prev=(row.get("Context") or "").split("⟦TARGET⟧")[0].strip(),
                    context_next=(row.get("Context") or "").split("⟦TARGET⟧")[-1].strip(),
                    pilot=(row.get("Pilot") or "").strip().upper() == "Y",
                    gold_label=Label(raw),
                    label_source=label_source,
                )
            )
    if skipped:
        print(f"  skipped {skipped} rows with no {column} value")
    return items


def build_gw1000(label_source: str = "llm_pre", master_csv: Path | None = None) -> Path:
    if label_source not in LABEL_SOURCES:
        raise ValueError(f"label_source must be one of {LABEL_SOURCES}")
    src = master_csv or MASTER_CSV
    if not src.exists():
        raise FileNotFoundError(f"master table not found: {src} (run kb/annotation/work/build_sheets.py)")
    items = _read_master(src, label_source)
    if not items:
        raise ValueError(f"no rows with a {label_source} label in {src}")
    digest = _hash_items(items)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out = EVAL_DIR / f"gw1000.{label_source}.{digest}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(it.model_dump_json() + "\n")
    return out


def _read_a3cg(path: Path) -> tuple[list[GoldItem], int]:
    """One item per (statement, aspect), the unit of A3CG's action-classification sub-task (AC).

    A3CG releases isolated statements with no company, year or page, so those fields stay empty and
    only `sentence_only` can run. A statement without aspects becomes one `none` row, as in gw1000.
    Aspects annotated with two different actions (the phrase occurs twice) have no single gold label
    and are skipped; the count is returned so it can be reported.
    """
    return a3cg_items(json.loads(path.read_text(encoding="utf-8")))


def a3cg_items(records: list[dict], provenance: dict[int, dict] | None = None) -> tuple[list[GoldItem], int]:
    """Expand A3CG records into per-aspect rows; `provenance` optionally maps sentence_id to the
    company / year / page / file / context fields recovered from our own corpus."""
    items: list[GoldItem] = []
    skipped = 0
    for rec in records:
        prov = (provenance or {}).get(rec["sentence_id"], {})
        category_of = {a: c for c, aspects in rec["aspect_categories"].items() for a in aspects}
        for i, (aspect, actions) in enumerate(rec["aspects"].items()):
            if len(set(actions)) != 1:
                skipped += 1
                continue
            no_aspect = aspect == "no aspect"
            items.append(GoldItem(
                item_id=f"{rec['sentence_id']}:{i}",
                text=rec["text"],
                aspect=None if no_aspect else aspect,
                category=None if no_aspect else category_of.get(aspect),
                company=prov.get("company", ""),
                year=prov.get("year", 0),
                page=prov.get("page"),
                file=prov.get("file"),
                context_prev=prov.get("context_prev", ""),
                context_next=prov.get("context_next", ""),
                gold_label=Label.NONE if no_aspect else Label(actions[0]),
                label_source="a3cg_gold",
            ))
    return items, skipped


def build_a3cg(root: Path | None = None) -> list[tuple[Path, int, int]]:
    """Freeze every A3CG test split; returns (snapshot, items, skipped multi-action aspects)."""
    out = []
    for dataset_id, rel in A3CG_SPLITS.items():
        src = (root or A3CG_DIR) / rel
        if not src.exists():
            raise FileNotFoundError(f"A3CG split not found: {src}")
        items, skipped = _read_a3cg(src)
        out.append((write_snapshot(dataset_id, "a3cg_gold", items, replace=True), len(items), skipped))
    return out


def write_snapshot(dataset_id: str, label_source: str, items: list[GoldItem], replace: bool = False) -> Path:
    """Write a hash-named snapshot. `replace` drops older snapshots of the same id, for sources that are
    fixed releases, so a rebuild replaces rather than accumulates."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    if replace:
        for old in EVAL_DIR.glob(f"{dataset_id}.{label_source}.*.jsonl"):
            old.unlink()
    path = EVAL_DIR / f"{dataset_id}.{label_source}.{_hash_items(items)}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(it.model_dump_json() + "\n")
    return path


def snapshot_path(dataset_id: str, label_source: str) -> Path:
    matches = sorted(EVAL_DIR.glob(f"{dataset_id}.{label_source}.*.jsonl"))
    if not matches:
        raise FileNotFoundError(
            f"no frozen snapshot for {dataset_id}/{label_source}. "
            f"Build one first: gw-data build {dataset_id} --labels {label_source}"
        )
    if len(matches) > 1:
        raise RuntimeError(
            "several snapshots exist, refusing to guess: " + ", ".join(m.name for m in matches)
        )
    return matches[0]


def load(dataset_id: str = "gw1000", label_source: str = "llm_pre") -> tuple[list[GoldItem], str]:
    path = snapshot_path(dataset_id, label_source)
    items = [GoldItem(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return items, path.name.split(".")[-2]
