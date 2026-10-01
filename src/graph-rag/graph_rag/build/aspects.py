"""Stage 2 (M1 version): aspect nodes and mentions.

Two deterministic sources, both auditable:

1. `gold_span` — the annotated span of an eval sentence, carrying its action label. The eval sentence
   is joined to the parsed statement by normalised text inside the same report, so a mention hangs on
   a real statement node with page provenance.
2. `string_match` — the same surface form found verbatim in other statements of the *same company*.
   This is what makes cross-year chains exist before any extractor runs. No action label is attached:
   an unlabelled mention says "this aspect is discussed here", nothing more.

M2 replaces the identity function (`aspect_key`) with clustering, gated on a purity audit; M3/D3 adds
LLM-extracted aspects. Until then a merge only happens when two surface forms are literally the same
words, which keeps false cross-year links out.
"""

from __future__ import annotations

import json
from collections import defaultdict

from pathlib import Path

from graph_rag.build.parse import eval_snapshot
from graph_rag.build.text import aspect_key, normalise
from graph_rag.config import GraphConfig
from graph_rag.extract import CATEGORIES, looks_like_sentence
from graph_rag.store.duckdb_store import DuckDBGraphStore


def _match_eval_to_statements(store: DuckDBGraphStore, items: list[dict]) -> tuple[dict[str, str], int]:
    """eval item_id -> stmt_id, matching on normalised text within the item's own report."""
    by_norm: dict[tuple[str, str], str] = {}
    for stmt_id, file, norm in store.con.execute(
        "SELECT s.stmt_id, r.file, s.norm_text FROM statements s JOIN reports r USING (sha256)"
    ).fetchall():
        by_norm.setdefault((file, norm), stmt_id)
    mapping, missing = {}, 0
    for it in items:
        key = (it["file"], normalise(it["text"]))
        stmt = by_norm.get(key)
        if stmt is None:
            missing += 1
            continue
        mapping[it["item_id"]] = stmt
    return mapping, missing


def ingest_extracted(
    store: DuckDBGraphStore, path: Path, verbose: bool = True
) -> dict:
    """Add aspects and mentions produced by the external extractor (decision D3, gate A8).

    Everything lands with `method='llm'`, never merged into `gold_span`, so any experiment can be
    re-run with or without the extracted half. Rejected rows are counted, never silently dropped.
    """
    by_stmt = {
        row[0]: row[1]
        for row in store.con.execute("SELECT stmt_id, text FROM statements").fetchall()
    }
    known_aspects = {row[0] for row in store.con.execute("SELECT aspect_id FROM aspects").fetchall()}

    new_aspects: dict[str, tuple[str, str]] = {}
    mentions: list[tuple] = []
    aliases: set[tuple[str, str, str]] = set()
    rejected = {"unknown_stmt_id": 0, "not_a_substring": 0, "bad_category": 0, "empty_span": 0}

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        text = by_stmt.get(rec["stmt_id"])
        if text is None:
            rejected["unknown_stmt_id"] += 1
            continue
        for span in rec.get("spans", []):
            surface = (span.get("text") or "").strip()
            category = (span.get("category") or "").strip().lower()
            if not surface:
                rejected["empty_span"] += 1
                continue
            if surface not in text:  # verbatim, case-sensitive: the prompt contract
                rejected["not_a_substring"] += 1
                continue
            if category not in CATEGORIES:
                rejected["bad_category"] += 1
                continue
            key = aspect_key(surface)
            if key not in known_aspects:
                new_aspects.setdefault(key, (surface, category))
            aliases.add((key, key, "llm"))
            mentions.append((rec["stmt_id"], key, None, None, "llm"))

    store.insert_many(
        "aspects", [(k, canon, cat, "llm") for k, (canon, cat) in sorted(new_aspects.items())], 4
    )
    store.insert_many("aspect_aliases", sorted(aliases), 3)
    store.insert_many("mentions", mentions, 5)
    stats = {
        "file": str(path),
        "new_aspects": len(new_aspects),
        "llm_mentions": len(mentions),
        "rejected": rejected,
    }
    if verbose:
        print(f"  ingested {len(mentions)} llm mentions, {len(new_aspects)} new aspects; "
              f"rejected {sum(rejected.values())} ({rejected})")
    return stats


def run(
    cfg: GraphConfig, store: DuckDBGraphStore, verbose: bool = True, extracted: str | None = None
) -> dict:
    items = eval_snapshot(cfg)
    store.clear("mentions", "aspect_aliases", "aspects")

    mapping, missing = _match_eval_to_statements(store, items)
    if verbose:
        print(f"  eval sentences matched to statements: {len(mapping)}/{len(items)} (missed {missing})")

    # ---- aspect nodes from the annotated spans
    aspects: dict[str, dict] = {}
    gold_mentions: list[tuple] = []
    for it in items:
        surface = it.get("aspect")
        if not surface or it["item_id"] not in mapping:
            continue
        key = aspect_key(surface)
        entry = aspects.setdefault(key, {"canonical": surface, "category": it.get("category"),
                                         "surfaces": set()})
        entry["surfaces"].add(surface)
        gold_mentions.append(
            (mapping[it["item_id"]], key, it["gold_label"], cfg.label_source, "gold_span")
        )

    store.insert_many(
        "aspects",
        [(k, v["canonical"], v["category"], "gold_span") for k, v in sorted(aspects.items())],
        4,
    )
    store.insert_many(
        "aspect_aliases",
        sorted({(aspect_key(s), k, "gold_span") for k, v in aspects.items() for s in v["surfaces"]}),
        3,
    )
    store.insert_many("mentions", gold_mentions, 5)

    # ---- string-match expansion, so a chain can exist across years
    searchable = {
        k: v for k, v in aspects.items()
        if len(k) >= cfg.min_surface_chars and len(k.split()) >= cfg.min_surface_tokens
    }
    if verbose:
        print(f"  aspects: {len(aspects)} total, {len(searchable)} long enough to string-match")

    labelled = {(m[0], m[1]) for m in gold_mentions}
    per_bucket: dict[tuple[str, str, int], int] = defaultdict(int)
    extra: list[tuple] = []
    skipped_junk = 0
    for key in sorted(searchable):
        rows = store.con.execute(
            """
            SELECT stmt_id, company, year, text FROM statements
            WHERE contains(norm_text, ?)
            ORDER BY year, stmt_id
            """,
            [key],
        ).fetchall()
        for stmt, company, year, text in rows:
            if (stmt, key) in labelled:
                continue
            # GRI content-index rows, table debris and page furniture contain the words but are not
            # statements; anchoring a cross-year link on them produces a chain that says nothing.
            if not looks_like_sentence(text):
                skipped_junk += 1
                continue
            bucket = (company, key, year)
            if per_bucket[bucket] >= cfg.max_string_matches_per_company_year:
                continue
            per_bucket[bucket] += 1
            extra.append((stmt, key, None, None, "string_match"))
    store.insert_many("mentions", extra, 5)

    extracted_stats = ingest_extracted(store, Path(extracted), verbose) if extracted else None

    stats = {
        "extracted": extracted_stats,
        "eval_items": len(items),
        "matched_statements": len(mapping),
        "unmatched_eval_items": missing,
        "aspects": len(aspects),
        "searchable_aspects": len(searchable),
        "gold_mentions": len(gold_mentions),
        "string_match_mentions": len(extra),
        "string_match_skipped_non_sentences": skipped_junk,
    }
    (cfg.out_dir / "aspects_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
