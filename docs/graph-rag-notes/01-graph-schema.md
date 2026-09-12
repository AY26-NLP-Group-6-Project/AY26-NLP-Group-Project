# 01 · Graph schema and build pipeline

Design rule: **every node and edge is either derived from metadata we already trust, or has a
provenance pointer and an accuracy gate.** Nothing is created by free-form LLM extraction without
a measurable check.

## 1. Nodes

| Node | Key | Fields | Source | Trust |
|---|---|---|---|---|
| `Company` | `sgx_code` | name, aliases | `kb/manifest.csv` | exact |
| `Report` | `sha256` | company, year, file, n_pages | `kb/manifest.csv` | exact |
| `Statement` | `stmt_id` | text, report, page, char_span, source (`eval` \| `corpus`) | sentence splitter (same code as the annotation set) | exact text, noisy page for merged fragments |
| `Aspect` | `aspect_id` | canonical_name, category, surface_forms[] | canonicalisation (M2) | gated, purity ≥0.8 |
| `Category` | code | A3CG Table 5 name + definition | fixed list of 10 | exact |
| `Metric` | `metric_id` | kind, value, unit, year, scope, basis (market/location), restated_flag | regex + unit table (M3) | gated, precision ≥0.9 |
| `Target` | `target_id` | kind, value, unit, target_year, baseline_year, status | regex + patterns (M3) | gated |

`Action` is **not** a node: it is an edge attribute, because the same aspect takes different actions
in different statements.

## 2. Edges

```
(Report)      -[:OF_COMPANY]->            (Company)
(Statement)   -[:IN_REPORT {page}]->      (Report)
(Statement)   -[:MENTIONS {action, label_source, confidence}]-> (Aspect)
(Aspect)      -[:IN_CATEGORY]->           (Category)
(Statement)   -[:REPORTS_METRIC]->        (Metric)
(Statement)   -[:SETS_TARGET]->           (Target)
(Metric)      -[:MEASURES]->              (Aspect)
(Target)      -[:TARGETS]->               (Aspect)
(Statement)   -[:FOLLOWS_UP {years_apart}]-> (Statement)   # derived, same company + aspect
(Target)      -[:REVISED_BY {delta, baseline_changed}]-> (Target)
```

`FOLLOWS_UP` and `REVISED_BY` are **derived** edges — they are the product, not an input. They are
what the trajectory query and the "moved goalposts" check read.

## 3. Aspect canonicalisation (M2, the critical step)

Input: aspect surface forms. For the eval set these are our annotated spans; for the wider corpus an
LLM extracts them, prompted with the A3CG aspect rules (D3). Extraction quality is gated by A8:
score the extractor against our 1,000 gold spans (span match + category accuracy) before its output
is allowed to create edges.

Pipeline:

1. **Normalise** — lowercase, strip determiners/possessives (`our`, `the`, `its`), expand known
   abbreviations (`GHG`, `OHS`, `PDPA`), singularise head noun, drop bracketed acronyms already
   present as a separate form.
2. **Block** — group by category first, so `waste management` (WM) never merges with
   `waste of resources` (RO).
3. **Embed and cluster** — `bge-m3` embeddings, agglomerative clustering with a cosine threshold
   tuned on a held-out sample; centroid surface form becomes `canonical_name`.
4. **Alias table** — a reviewable `aspects_alias.csv` (`surface_form, aspect_id, method`), so a human
   can override any merge. Overrides are versioned with the graph build.
5. **Audit** — sample 100 clusters, count wrong merges / missed merges, report purity. Gate: ≥0.8.

Fallback if the gate fails: exact normalised string match only. That yields a sparser graph but no
false cross-year links, which is the safer failure mode.

## 4. Metric and target extraction (M3)

Deterministic, unit-aware, and deliberately narrow:

- **Emissions**: `Scope 1|2|3`, `tCO2e|tCO₂e|tonnes CO2`, market-based vs location-based basis.
- **Energy**: `kWh|MWh|GJ`, renewable share `%`.
- **Water**: `m³|ML|litres`, intensity per unit.
- **Waste**: `tonnes`, recycled `%`, diverted-from-landfill `%`.
- **Safety**: LTIR, fatalities, incident counts.
- **Targets**: `by 20\d\d`, `\d+% reduction`, `net[- ]zero`, `baseline (year )?20\d\d`, `vs 20\d\d`.

Each extraction keeps `{statement_id, char_span, raw_text}`. Anything that fails unit validation is
dropped, not guessed. Numbers inside table fragments are flagged (`from_table=true`) because our
sentence pipeline is known to mangle tables.

## 4b. What traversal returns

Graph retrieval returns **Statement nodes with their text, page and provenance**, plus any Metric or
Target attached to the same aspect. It never returns bare entities or relation triples: on specific
QA, methods that return only graph structure lose to plain vector RAG, while retaining the original
text chunks is what makes retrieval work (arXiv 2503.04338, Exp.1). The graph decides *which*
statements to fetch; the statements themselves are the evidence.

## 5. Storage

Decision D1: **DuckDB** for node/edge tables (`nodes_*.parquet` semantics, SQL joins, zero infra)
plus **networkx** loaded on demand for multi-hop traversal on the filtered subgraph
(a company's subgraph is small — hundreds of nodes).

`GraphStore` is a Protocol in `src/graph-rag`; `DuckDBGraphStore` is the only implementation we
build (D1). The Protocol stays so a Neo4j backend remains possible later without touching callers.
Nothing above the store layer may import DuckDB or Neo4j directly.

## 6. Build pipeline

```
kb/manifest.csv + kb/raw/*.pdf
   │  (reuse of the annotation-set code path)
   ├─ parse      → statements.parquet        {stmt_id, text, sha256, page, company, year}
   ├─ aspects    → mentions.parquet          {stmt_id, surface_form, category, action, label_source}
   ├─ canonical  → aspects.parquet + aspects_alias.csv
   ├─ measures   → metrics.parquet, targets.parquet
   └─ derive     → follows_up.parquet, target_revisions.parquet
                         │
                         └─ graph.duckdb  (+ build_manifest.json: git sha, config hash, counts)
```

Every stage is a separate `uv run` command, idempotent, writing to `artifacts/graph/<build_id>/`.
A build is never overwritten; the eval harness records which `build_id` it ran against.

## 7. M1 status (what is actually built)

Stages `parse`, `aspects`, `derive` are implemented and run over the D2 scope: the 52 companies the
eval set touches, all of their kept reports 2020-2025 (233 reports, ~10.5k pages).

Two deliberate simplifications, both replaced later:

- **Aspect identity is normalised exact match** (`aspect_key`: lowercase, strip punctuation, drop a
  leading determiner or possessive). No clustering yet, so two spans merge only when they are the
  same words. Sparser graph, no false cross-year links. M2 replaces this, gated on purity >= 0.8.
- **Mentions come from two sources**: `gold_span` (the annotated span of an eval sentence, carrying
  its action label) and `string_match` (the same surface form found verbatim in another statement of
  the same company, with **no** action label). String matching is what makes cross-year chains exist
  before any extractor runs; it is capped per (company, aspect, year) and skips spans shorter than
  10 characters or 2 tokens, so generic aspects like "waste" or "data" cannot flood the graph.
  M3/D3 replaces it with LLM extraction, gated by A8.
