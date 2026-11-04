"""File-exchange interface, for work that happens outside this package.

The retrieval team can answer the same questions without importing `gw_common`:

    gw-eval export-queries --condition cross_year_rrf --out queries.jsonl
    # ... their code writes evidence.jsonl: {"item_id": ..., "spans": [{text, company, year, ...}]}
    gw-eval run --system graph-rag --evidence evidence.jsonl --condition cross_year_rrf

A system that produces labels itself skips the classifier entirely:

    gw-eval score --predictions preds.jsonl --condition cross_year_rrf

Queries never carry the gold label, and evidence read back in goes through the same target-sentence
filter as in-process retrieval, so an outside retriever cannot win by returning the target.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from gw_common.schemas import Citation, EvidenceCondition, EvidenceSpan, GoldItem, Label, Prediction


def export_queries(
    items: Sequence[GoldItem], condition: EvidenceCondition, out: Path, k: int = 3
) -> dict:
    """One line per item: what a retriever is allowed to know, plus the filters it must honour."""
    with out.open("w", encoding="utf-8") as f:
        for it in items:
            cross_year = condition.value.startswith("cross_year") or condition.value == "company_agentic"
            f.write(json.dumps({
                "item_id": it.item_id,
                "condition": condition.value,
                "k": k,
                "text": it.text,
                "aspect": it.aspect,
                "company": it.company,
                "sgx_code": it.sgx_code,
                "anchor_year": it.year,
                "year_from": None if cross_year else it.year,
                "year_to": None if cross_year else it.year,
                "page": it.page,
                "file": it.file,
                "exclude_target_sentence": True,
            }) + "\n")
    return {"queries": len(items), "condition": condition.value, "k": k, "out": str(out)}


def read_evidence(path: Path) -> dict[str, list[EvidenceSpan]]:
    """Read `{item_id, spans[]}` lines. Spans need text, company and year; the rest is optional."""
    out: dict[str, list[EvidenceSpan]] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            spans = [
                EvidenceSpan(
                    statement_id=str(s.get("statement_id") or s.get("id") or f"{line_no}:{i}"),
                    text=s["text"], company=s.get("company", ""), year=int(s["year"]),
                    page=s.get("page"), file=s.get("file"), score=float(s.get("score", 0.0)),
                    why=s.get("why", "external"),
                )
                for i, s in enumerate(record.get("spans", []))
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{path}:{line_no}: bad evidence record ({exc})") from exc
        out[str(record["item_id"])] = spans
    return out


def read_predictions(path: Path) -> dict[str, Prediction]:
    """Read `{item_id, label}` lines from a system that classifies on its own.

    Optional per line: `rationale` (text) and `citations`, a list of `{ref, statement_id?, company?,
    year?, page?, file?, quote?}`; without them the grounding metrics simply report no rationale."""
    out: dict[str, Prediction] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        try:
            label = Label(str(record["label"]).strip().lower())
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: {record.get('label')!r} is not a label") from exc
        out[str(record["item_id"])] = Prediction(
            item_id=str(record["item_id"]),
            label=label,
            evidence_ids=[str(e) for e in record.get("evidence_ids", [])],
            rationale=str(record.get("rationale") or ""),
            citations=[Citation(**c) for c in record.get("citations", [])],
            latency_ms=float(record.get("latency_ms", 0.0)),
            input_tokens=int(record.get("input_tokens", 0)),
            output_tokens=int(record.get("output_tokens", 0)),
            llm_calls=int(record.get("llm_calls", 0)),
        )
    return out


def align(items: Sequence[GoldItem], supplied: dict, what: str) -> tuple[list, list[str]]:
    """Line up supplied records with the selected items; report what is missing."""
    missing = [it.item_id for it in items if it.item_id not in supplied]
    if missing and len(missing) == len(items):
        raise ValueError(f"no {what} matched the selected items (first id: {items[0].item_id})")
    return [supplied.get(it.item_id) for it in items], missing
