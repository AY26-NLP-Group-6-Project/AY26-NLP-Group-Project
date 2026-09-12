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

LABEL_SOURCES = ("llm_pre", "human_majority")


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
