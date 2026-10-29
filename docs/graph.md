# The temporal claim graph

What the graph line built, what it contains, how it is built, and what the graph arms retrieve. The
measured results are in `results.md`; the dated record in `history.md`.

## 1. Why a graph

Hybrid retrieval ranks passages by similarity. Three things the project needs are not similarity
problems:

1. **Same company, same aspect, other year.** ESG language is templated, so nearest-neighbour search
   returns other companies' near-identical sentences. What is wanted is an exact join on
   `(company, aspect, year)`.
2. **Promise follow-up.** "Did the 2022 commitment become an implemented statement or a figure by
   2024?" is a join across years, not a ranking.
3. **Moved goalposts.** A changed baseline year, a restated figure or a quietly dropped target is a
   comparison between structured records.

An ESG knowledge graph with graph RAG already exists (EmeraldMind, `evidence-ledger.md`) but has no
temporal dimension; A3CG never compares across years. The defensible contribution is therefore a
*temporal* claim graph, not "an ESG knowledge graph". Design rule: every node and edge is either
derived from metadata already trusted, or carries a provenance pointer and an accuracy gate.

Out of scope, on purpose: open-domain entity extraction over the whole corpus with nothing to validate
it against; community summarisation in the style of Microsoft GraphRAG (our queries are local and
structured); free-form agents.

## 2. What is in the graph

Store: DuckDB (`artifacts/graph/dev/graph.duckdb`), with networkx loaded on demand for traversal of a
company's subgraph. `DuckDBGraphStore` is the only implementation; the `GraphStore` Protocol keeps a
Neo4j backend possible without touching callers.

| table | rows | what |
|---|---|---|
| `companies` | 56 | SGX code, name |
| `reports` | 240 | sha256, company, year (2020–2025), file, pages |
| `statements` | 110,314 | sentence-split text with `{company, year, page, idx}`; every one of the 1,000 evaluation sentences matches a statement by normalised text inside its own report |
| `aspects` | 7,503 | sustainability aspects: 734 from the annotated spans and their string matches, 6,769 extracted by an LLM |
| `aspect_aliases`, `aspect_canon` | 7,503 each | surface form → aspect id, and aspect → canonical id (morph normalisation, 7,319 canonical ids) |
| `mentions` | 29,637 | statement → aspect, with the action label where one exists (`gold_span`), `string_match`, or `llm` |
| `follows_up` | 8,524 | statement → later statement of the same company and aspect, with `years_apart` and `same_text`; 28 % link verbatim repeats |

`Action` is an edge attribute of `mentions`, not a node, because the same aspect takes different
actions in different statements. The `Metric` and `Target` nodes of the original design were never
built as regex extractions; dated targets are instead extracted by an LLM with mechanical validation and
kept as the promise tables under `artifacts/graph/dev/promises/` (`promises.md`).

Two findings from the first build that shaped it: page furniture (GRI content-index rows repeated
every year) produced thousands of false chains until a sentence-shape gate on candidate mentions
dropped 23,097 of them (the gate applies to what the aspect extractor sees, not to what the arms
retrieve); and 27–28 % of cross-year edges join two identical sentences a year apart, which is a fact
about templated reporting, so edges carry `same_text` and the trajectory logic can tell a progressed
claim from a copied paragraph.

## 3. How it is built

```
kb/manifest.csv + kb/raw/*.pdf
   ├─ parse      → statements                (the sentence splitter of the annotation set)
   ├─ aspects    → mentions                  (gold spans, string matches, LLM extraction)
   ├─ canonical  → aspect_canon              (morph normalisation; HAC + LLM verification measured and rejected)
   └─ derive     → follows_up
```

```bash
uv run gw-graph build --config configs/graph.dev.yaml            # all stages
uv run gw-graph stats                                           # counts, cross-year chains
uv run gw-graph export-extract --per-report 40 --out ...         # statements for an outside extractor
uv run gw-graph score-extraction --pred your_output.jsonl        # the extraction gate
uv run gw-graph aspects --extracted your_output.jsonl; uv run gw-graph derive
uv run gw-graph canon-pools | canon-tune | canon-verify | canon-spotcheck | canon-spotcheck-score
```

Every stage writes to `artifacts/graph/<build_id>/` with a build manifest (git sha, config, counts); a
build is never overwritten, and every evaluation run records the build id.

### Aspect extraction

The 1,000 annotated sentences carry aspect spans; the other ~108,000 statements do not. An LLM of a
different family from the one that produced our labels extracted spans from 9,320 statements (40 per
report) under `configs/prompts/aspect_extraction.md` (`handoffs/aspect-extraction.md`). The gate, scored
on the 1,000 gold sentences: partial-match F1 ≥ 0.60, category accuracy ≥ 0.70, false-positive rate on
no-aspect sentences ≤ 0.35. Result: **0.649 / 0.903 / 0.264**, passed (category accuracy was 0.873
before 56 of our climate-risk pairs were re-mapped to A3CG's convention). Measured precision (0.58
partial) is a lower bound: a sample of unmatched spans was mostly further items in enumerations the gold
had skipped. Ingestion rejects any span that is not a verbatim substring, any unknown statement id and any
category outside the ten, and reports the counts.

Effect: 29,637 mentions, 7,503 aspect nodes, 3,932 cross-year chains. But **5,334 of the 6,769 new
aspect nodes (79 %) occur exactly once**: free-text spans fragment ("scope 1 and 2 emissions", "scope 1
and scope 2 ghg emissions", "direct emissions" never meet). Canonicalisation, not extraction, is the
binding constraint.

### Canonicalisation

Method under test (CESI, `evidence-ledger.md`): embed the phrases, complete-linkage HAC with a cosine
threshold tuned on validation pools, reported on test pools; then, as an improvement, let HAC propose
candidates (top 5 neighbours, cosine ≥ 0.70) and an LLM verify each pair under the gold guideline
written as matching rules (`handoffs/canonicalisation-gold.md`).

Gold: pools of up to 12 phrases from one category (an anchor, its 5 nearest by embedding, 4 nearest by
word overlap, 2 random), partitioned into same-aspect groups by an annotator who had not seen any
clustering output, under "when unsure, keep apart". Gate: pairwise precision ≥ 0.80 on test pools, the
threshold selected by pairwise F0.5 on validation pools. (The first gate, micro precision, was abandoned
because 87 % of gold clusters are singletons and merging nothing maximised it.)

Result on a clean test set (81 pools, 811 phrases, 123 gold pairs, labelled before any method ran):

| method | pairwise precision | recall | F1 |
|---|---|---|---|
| morph normalisation only | 1.000 | 0.000 | 0.000 |
| embeddings + HAC at 0.82 | 0.467 [0.37–0.58] | 0.463 | 0.465 |
| embeddings propose, LLM verifies | 0.597 [0.49–0.70] | 0.748 [0.63–0.87] | 0.664 |

The verifier accepts most gold pairs (106 of 123) and also 76 non-gold pairs, two thirds of which break
the rules it was given (broader vs narrower, thing vs instrument, class vs instance). **The gate failed;
the graph keeps morph normalisation** (7,503 → 7,319 ids, 184 merges). An earlier figure of 0.733 came
from test pools that had been looked at twice and was optimistic by about 0.14. A blind spot-check of
the gold (66 pairs from 10 pools, `handoffs/canonicalisation-spotcheck.md`) was exported for a teammate
and never filled, so whether the gold is stricter than people are remains unmeasured.

## 4. What the graph arms retrieve

Both arms return statements with their text, page and file, never bare nodes, because on specific
questions graph-only methods lose to plain vector RAG (`evidence-ledger.md`).

| arm | how | coverage on dev | retrieval p50 |
|---|---|---|---|
| `cross_year_graph` | the item's aspect → its morph group → statements of the same company in other years that mention it, verbatim repeats of the target skipped | 0.40 | about 9 ms |
| `cross_year_fused` | the graph arm first, then BM25 over the company's other-year statements fills to k = 3 | 0.89 | about 20 ms |

Both arms retrieve over every statement of five words or more, the same knowledge base as the baseline
(`baseline.md`); the sentence-shape gate decides only which statements the aspect extractor labelled.

What they achieve on RQ1 against the hybrid baseline is in `results.md`: the same accuracy, at a tenth
of the retrieval latency. For RQ2 the graph's join is the promise table's `related` link (same company
and metric, another deadline or level); the aspect nodes are not used there, since they cover 29,637
statements of 110,314.

## 5. Decisions and status

| decision | consequence |
|---|---|
| store = DuckDB + networkx, no Neo4j service | one implementation, the Protocol stays |
| the graph is built over the whole corpus (240 reports) rather than the evaluation companies only | the stores the baseline and the graph retrieve from are the same statements |
| aspects outside the annotated sentences come from an LLM, gated | gate passed; see above |
| the agentic arm belongs in the main comparison, with cost and latency as first-class metrics | not built; a stub remains |

Status of the original phase plan:

| phase | status |
|---|---|
| scaffold: workspace, contracts, harness | done |
| graph build | done, 240 reports, counts above |
| aspect canonicalisation | **gate failed**; morph normalisation kept |
| metric and target extraction by regex | replaced by LLM target extraction with validation (`promises.md`) |
| retrieval arm in the RQ1 ablation | done; same accuracy as hybrid retrieval, faster |
| trajectories | done as the promise pipeline, judged against human checks (`promises.md`) |
| serving | FastAPI app exists (`evaluation.md`); no front end |
| agentic arm | stub |

Risks that materialised: canonicalisation was the whole ball game for cross-year aspect edges, and it
failed its gate; extraction noise from tables and ligatures reached the promise pipeline and had to be
handled there (verbatim-span rule, neighbour statements, a judge that reads flattened tables with care).
