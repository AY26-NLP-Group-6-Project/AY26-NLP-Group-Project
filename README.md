# Greenwash-RAG

Evidence-grounded, cross-year tracking of sustainability claims in SGX-listed companies' reports.

Two questions. **RQ1:** given a sentence from a report and a candidate aspect ("Scope 3 emissions"),
does evidence retrieved from the company's own reports change the label a model gives it
(implemented / planning / indeterminate / none, the A3CG scheme)? **RQ2:** when a report makes a dated
commitment, what do the company's later reports say became of it?

This README is the operating manual: setup, running an evaluation, plugging in a system, where things
are. The reference and the record are under [`docs/`](docs/README.md); the findings are in
[`docs/results.md`](docs/results.md).

## 1. Requirements

| | |
|---|---|
| Python | 3.12 (`.python-version`), [uv](https://docs.astral.sh/uv/) |
| Chat model | `gpt-5.6-luna`, reasoning effort low; fixed for the whole project so runs stay comparable |
| Embeddings | `text-embedding-3-small` (1536 dims); query vectors must come from the same model as the stored ones |
| Reranker | `Xenova/ms-marco-MiniLM-L-6-v2` via fastembed (ONNX, CPU, about 90 MB on first use) |
| Docker (optional) | for the shared Postgres + pgvector store |
| Keys | an OpenAI-compatible key for chat and one for embeddings, in `.env`; never committed |

| data | where it sits | how you get it |
|---|---|---|
| frozen evaluation set, 1,000 sentences | `data/eval/gw1000.*.jsonl` | in git; built from `kb/annotation/eval.xlsx` |
| frozen RQ2 gold, 373 dated commitments with their outcome and split | `data/eval/rq2promises.*.jsonl` | in git; `gw-graph promise-gold` from the group's sheet and `kb/annotation/rq2-gold/` |
| the knowledge base: every statement of five words or more, 108,376 chunks with vectors and a manifest (`passages`, 18,839 windows of 200 words, is the granularity ablation) | `artifacts/baseline/statements/` | `gw-kb-statements-<hash>.zip` shared inside the group, or `gw-baseline build` from the parsed corpus |
| parsed corpus and claim graph (`graph-rag` only) | `artifacts/graph/dev/graph.duckdb` | `gw-graph build` from the raw PDFs, or a copy from a teammate |
| raw reports | `kb/raw/` | never redistributed; `kb/README.md` |

## 2. Setup

```bash
uv sync                                        # the workspace: src/common, src/baseline-rag, src/graph-rag, src/example-rag
cp .env.example .env                           # fill LLM_API_KEY and EMB_API_KEY; model, effort and prices are set
unzip gw-kb-statements-<hash>.zip -d artifacts/baseline/
uv run gw-baseline stats                       # the manifest; hash d8a62bfe40c6
uv run gw-data list                            # the versioned snapshots
uv run pytest -q                               # no network needed
uv run gw-eval --system example-rag --split dev --sample 20 --repeats 1     # smoke run
```

Optional shared database (the same chunks served by pgvector):

```bash
docker compose up -d
uv run gw-baseline pg-import && uv run gw-baseline pg-check
GW_BASELINE_BACKEND=postgres uv run gw-eval --system baseline-rag --split dev --repeats 3
```

`.env` keys that matter (the full list, with comments, is in `.env.example`):

```
LLM_API_KEY / LLM_BASE_URL / LLM_MODEL          chat model
EMB_API_KEY / EMB_BASE_URL / EMB_MODEL          embeddings
LLM_REASONING_EFFORT=low                        fixed for experiments
GW_LLM_CACHE=1                                  SQLite response cache; bypassed automatically when --repeats > 1
GW_CLASSIFIER_STYLE=cited                       cited (label + rationale + citations) | label (one word)
LLM_PRICE_IN_PER_MTOK / LLM_PRICE_OUT_PER_MTOK  USD per million tokens; unset = tokens reported, no dollars
EMB_PRICE_PER_MTOK                              same, for query embeddings
GW_BASELINE_BUILD=statements                    statements (default) | passages, the granularity ablation
GW_BASELINE_MODE=rrf+rerank                     bm25 | dense | rrf | rrf+rerank
GW_BASELINE_BACKEND=files                       files | postgres
PG_DSN=postgresql://gw:gw@localhost:5432/gw
```

## 3. Running an evaluation

```bash
uv run gw-eval --list                                                        # registered systems
uv run gw-eval --system baseline-rag --split dev --repeats 3 \
               --conditions sentence_only,local,same_report_rrf,cross_year_rrf
uv run gw-eval --system graph-rag --split dev --repeats 3 \
               --conditions sentence_only,local,cross_year_graph,cross_year_fused
uv run gw-eval --task rq2 --system baseline-rag --split dev --repeats 3     # RQ2: promise outcomes, shared judge
uv run gw-eval --publish artifacts/runs/<run_id> --name <group>/<what-it-is> --note "one line"
uv run gw-eval --compare results/baseline/statement-hybrid-cited results/graph/graph-arms-cited
uv run gw-eval --ragas artifacts/runs/<run_id>                               # RAG metrics, scored afterwards
```

A run writes `artifacts/runs/<run_id>/` (manifest, predictions, evidence, metrics, report).
`--publish` copies the small parts into `results/<group>/<name>/` and updates `results/README.md`.
`--compare` pairs two runs on the same items and reports McNemar p per condition: that, not a
difference of means, is how systems are compared. Everything about conditions, metrics, flags and
outputs: [`docs/evaluation.md`](docs/evaluation.md).

The promise pipeline (RQ2) has its own commands under `gw-graph promise-*`:
[`docs/promises.md`](docs/promises.md). Its gold set has a dev/test split like the sentence set, and
`gw-eval --task rq2` evaluates any system's retriever on it with the shared judge; open test once.

A demo front end runs one dev item at a time through a registered system, step by step, against the
gold, with the evidence, the citations, the timings and the cost ([`frontend/README.md`](frontend/README.md)):

```bash
uv sync --group frontend && uv run streamlit run frontend/app.py
```

## 4. Plugging in your own system

Copy `src/example-rag` to `src/<you>-rag`, rename it, add it to the workspace members in
`pyproject.toml`, `uv sync`. Replace the retriever; keep the shared classifier unless the classifier is
your contribution. A retriever may read the corpus through the shared tools
(`gw_common.corpus.load("statements")`: search in four modes, a statement's neighbours, a page, a
company's reports; `load("graph")` adds the claim graph's joins), so an agent plans over the same calls
the fixed baseline makes. One `retrieve(query, k)` serves both questions: for RQ2 the query arrives
under the `promise_window` condition with the company, the year window and the promise record in
`query.meta`; the shared judge reads what comes back. Develop on `--split dev`; when a configuration is worth keeping, run it with
`--repeats 3`, publish it with a descriptive name and commit `results/`. The Protocols, the field
contract, the file-exchange path for code that is not Python and the retrieval-only evaluation are in
[`docs/evaluation.md`](docs/evaluation.md), section 8.

## 5. Layout

```
src/common/gw_common/        shared contract and harness: schemas, Protocols, registry, the corpus
                             tools (search, neighbours, pages, reports), datasets, runner, metrics,
                             report, LLM client, classifier, FastAPI app
src/baseline-rag/            BM25 + dense + RRF + rerank over the chunk stores; Postgres backend
src/graph-rag/               the temporal claim graph, graph and fused retrieval, the promise pipeline
src/example-rag/             copy-me template for a new system
frontend/                    Streamlit demo: one dev item through one system, with the evidence and the gold
configs/prompts/             every prompt, versioned; action_classifier_cited.md is the shared classifier
configs/graph.dev.yaml       graph build config
data/eval/                   frozen evaluation snapshots, one file per (dataset, label source, hash)
artifacts/                   git-ignored: runs, chunk stores, the graph, the LLM cache
results/                     published runs: results/baseline/<name>/, results/graph/<name>/
docs/                        reference and record (docs/README.md)
kb/                          kb/raw/ the reports (git-ignored); kb/annotation/ the evaluation set, the
                             human check sheets and their scores
tests/                       pytest
```

## 6. Rules

1. **Dev for tuning, test once.** Anything looked at while changing a prompt, threshold or retriever
   setting is dev; test (669 rows) is opened once, for the report.
2. **Repeats ≥ 3, cache bypassed.** The model re-samples; report mean ± sd and the majority vote.
3. **Paired tests across systems.** Independent runs of one configuration differ by about 0.025
   macro-F1 on their own.
4. **Same classifier, same budget** for every retrieval arm; if you change either, re-run every arm.
5. **Never feed the gold; never return the target sentence.** The harness strips the one and drops the
   other, and counts the drops.
6. **Provenance.** Every number in a document carries its run folder, snapshot hash and store hash.
7. **Data.** Raw PDFs stay in `kb/raw/`; the chunk-store packages are derived text for academic use
   inside the group; A3CG snapshots are for reference runs only and are not redistributed.
8. **Commits.** One line, prefixed (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), one per finished step.
