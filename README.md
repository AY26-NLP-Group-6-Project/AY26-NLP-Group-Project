# Greenwash-RAG

Evidence-grounded, cross-year tracking of sustainability claims in SGX-listed companies' reports.
Given a sentence from a report and one candidate aspect (for example "Scope 3 emissions"), a system
retrieves evidence from the company's own reports and labels the sentence **implemented / planning /
indeterminate / none**, following the A3CG scheme (Ong et al., ACL 2025). The research question is
whether retrieved evidence changes and improves that label compared with reading the sentence alone.

This README is the operating manual: how to set the repo up, how to run an evaluation, how to plug in
your own retriever or classifier, what the numbers mean and what not to do. It takes no position on
which system is better; that is what the evaluation is for. The proposal is in
[`docs/proposals/Greenwash RAG/`](docs/proposals/Greenwash%20RAG/README.md); the shared contracts
(`01`–`04`) and the graph-RAG line's own design notes and experiment log are in
[`docs/graph-rag-notes/`](docs/graph-rag-notes/README.md).

---

## 1. Requirements

| | |
|---|---|
| Python | 3.12 (pinned in `.python-version`) |
| Package manager | [uv](https://docs.astral.sh/uv/) — `uv sync` installs the workspace and the dev tools |
| Chat model | `gpt-5.6-luna`, reasoning effort **low**, temperature not applied (the model rejects it). Fixed for the whole project so runs stay comparable |
| Embeddings | `text-embedding-3-small` (1536 dims). Query vectors must come from the same model as the stored ones |
| Reranker | `Xenova/ms-marco-MiniLM-L-6-v2` via fastembed (ONNX, CPU, downloaded on first use, ~90 MB) |
| Docker (optional) | Docker Desktop / Compose v2, for the shared Postgres + pgvector store |
| Disk | ~1 GB: passage store 150 MB, LLM response cache, run directories |
| Keys | an OpenAI-compatible key for chat and one for embeddings, in `.env` (see below). Never commit `.env` |

Data and where it comes from (the evaluation set is versioned; the corpus-derived stores are distributed inside the group):

| what | where it must sit | how you get it |
|---|---|---|
| passage store (18,839 passages + vectors + manifest) | `artifacts/baseline/dev/` | the `gw-kb-dev-<hash>.zip` package, or `gw-baseline build` if you hold the parsed corpus |
| frozen evaluation snapshot | `data/eval/gw1000.*.jsonl` | **in git** (built from `kb/annotation/eval.xlsx`, also versioned); rebuild with `gw-data build gw1000` only after an annotation change |
| parsed corpus and claim graph (`graph-rag` only) | `artifacts/graph/dev/graph.duckdb` | `gw-graph build`, needs the raw PDFs under `kb/raw/` |
| raw reports | `kb/raw/` | never redistributed; see `kb/README.md` |

## 2. Setup

```bash
uv sync                                   # workspace: src/common, src/baseline-rag, src/graph-rag
cp .env.example .env                      # fill LLM_API_KEY, LLM_MODEL=gpt-5.6-luna, EMB_API_KEY
unzip gw-kb-dev-<hash>.zip -d artifacts/baseline/    # -> artifacts/baseline/dev/{chunks.jsonl,embeddings.npy,manifest.json}
uv run gw-baseline stats                  # prints the manifest; hash must match the package README
uv run gw-data list                       # the versioned eval snapshots in data/eval/ (hashes must match git)
uv run pytest -q                          # 52 tests, no network needed
```

Optional shared database (same passages, served by pgvector):

```bash
docker compose up -d                      # pgvector/pgvector:pg16, schema from deploy/postgres/init.sql
uv run gw-baseline pg-import --build-id dev
uv run gw-baseline pg-check  --build-id dev          # row count + text hash must equal the files
GW_BASELINE_BACKEND=postgres uv run gw-eval --system baseline-rag --split dev --repeats 3
```

`.env` keys that matter (full list with comments in `.env.example`):

```
LLM_API_KEY / LLM_BASE_URL / LLM_MODEL          chat model
EMB_API_KEY / EMB_BASE_URL / EMB_MODEL          embeddings
LLM_REASONING_EFFORT=low                        fixed for experiments
GW_LLM_CACHE=1                                  SQLite response cache; bypassed automatically when --repeats > 1
GW_CLASSIFIER_STYLE=cited                       cited (label + rationale + cited sources) | label (v1, one word)
LLM_PRICE_IN_PER_MTOK / LLM_PRICE_OUT_PER_MTOK  USD per million tokens; unset = tokens reported, no dollars
EMB_PRICE_PER_MTOK                              same, for query embeddings
GW_BASELINE_BUILD=dev                           which passage store; dev-sent is the sentence-unit ablation store
GW_BASELINE_MODE=rrf+rerank                     bm25 | dense | rrf | rrf+rerank
GW_BASELINE_BACKEND=files                       files | postgres
PG_DSN=postgresql://gw:gw@localhost:5432/gw
```

## 3. Layout

```
src/common/gw_common/        shared contract and harness (schemas, Protocols, registry, datasets,
                             eval runner/metrics/report, shared LLM client and classifier, FastAPI)
src/baseline-rag/            hybrid BM25 + dense + RRF + rerank over the passage store; Postgres backend
src/graph-rag/               temporal claim graph (DuckDB + networkx), graph/fused retrieval, agentic stub
configs/prompts/             every prompt, versioned; action_classifier_cited.md is the shared classifier
                             prompt (action_classifier.md is its label-only v1)
configs/graph.dev.yaml       graph build config
data/eval/                   frozen gw1000 snapshots (versioned), one file per (dataset, label source, hash);
                             A3CG-derived snapshots are local only
artifacts/runs/<run_id>/     one directory per evaluation run (see §4.4)
artifacts/baseline/<build>/  passage stores; artifacts/graph/<build>/ the graph
docs/graph-rag-notes/        roadmap, contracts, experiment log (sections 4b–4k), literature screens
kb/                          kb/raw/ the reports (git-ignored, see kb/README.md); kb/annotation/ the workbook,
                             aspect overrides and their README (versioned)
tests/                       pytest; hand-checked metric values, contract tests, retriever tests
```

## 4. Evaluation

### 4.1 Data

`gw1000`: 1,000 sentences from 52 issuers' 2023–2025 reports, each with one candidate aspect and its
A3CG category (or none), page-level provenance and neighbouring sentences. Human labels from six
annotators (Fleiss κ 0.809 on the 50-row pilot, all six annotators; the remaining 950 rows one
annotator each), one tie adjudicated.

| slice | rows | note |
|---|---|---|
| aspect rows with an action label | 796 | **the primary-metric population** |
| aspect rows labelled `none` | 7 | the proposed aspect was rejected |
| no-aspect rows labelled `none` | 163 | |
| no-aspect rows with an action label | 34 | annotators saw an aspect the proposer missed; spans filled in by review (already in `eval.xlsx`; trail in `kb/annotation/aspect_overrides.csv`), flagged `aspect_source=human_filled`. Reported separately, never inside the headline |

Frozen split, stratified by row type × label × category: **dev 331 / test 669**. Pilot rows are pinned
to dev. Tune on dev; open test once, for the report.

Label sources: `human_majority` (the gold), `llm_pre_{claude,deepseek,gpt}` (pre-annotations, for
label-noise analysis only), `a3cg_gold` (A3CG's released test splits, reference only — their aspects are
given, their statements carry no provenance, and the release may be in the LLM's training data).

```bash
uv run gw-data build gw1000                         # kb/annotation/eval.xlsx -> snapshots + build report (κ, counts)
uv run gw-data export-xls                           # kb/annotation/eval.xls, the file name the course brief asks for
uv run gw-data describe gw1000 --split dev          # counts per slice
uv run gw-data build a3cg                           # A3CG test splits as action-classification snapshots
```

### 4.2 Evidence conditions

One classifier, one prompt (`configs/prompts/action_classifier_cited.md`); systems differ only in the evidence
they hand it, at most `k = 3` spans of ≤ 800 characters each.

| condition | evidence the classifier sees | who provides it |
|---|---|---|
| `sentence_only` | nothing (A3CG setting; the baseline every delta is measured against) | harness |
| `local` | the neighbouring sentences from the same page | harness (item fields) |
| `same_report_rrf` | passages/sentences retrieved from the **same report** | system's retriever |
| `cross_year_rrf` | retrieved from the **same company, other years** | system's retriever |
| `cross_year_graph` | statements reached through the claim graph | graph-rag |
| `cross_year_fused` | graph first, BM25 over the company's other-year statements fills to k | graph-rag |
| `cross_year_agentic` | bounded plan–retrieve–stop loop (stub) | not yet |

The harness drops any returned span that *is* the target sentence (same company-year, text equal or
containing it) and reports how many it dropped (`evidence.target_dropped`), so no arm can score by
re-reading the sentence it classifies.

### 4.3 Running

```bash
uv run gw-eval --list                                                       # registered systems
uv run gw-eval --system baseline-rag --split dev --repeats 3 \
               --conditions sentence_only,local,same_report_rrf,cross_year_rrf
uv run gw-eval --system graph-rag    --split dev --repeats 3 \
               --conditions sentence_only,local,cross_year_graph,cross_year_fused
uv run gw-eval --system graph-rag --split dev --slice row_type=aspect,category=workplace|management
uv run gw-eval --system graph-rag --split dev --sample 60 --repeats 1      # quick smoke test
uv run gw-eval --compare artifacts/runs/<A> artifacts/runs/<B>
```

Flags: `--split dev|test|all`, `--slice key=v1|v2,…` (keys: split, row_type, aspect_source, category,
company, year, pilot, has_aspect, gold, agreement, aspect_weak), `--sample N` (seeded), `--limit N`,
`--repeats N` (default 3; bypasses the LLM cache so each repeat re-samples the model), `--baseline`
(default `sentence_only`), `--k`, `--labels`, `--dataset`.

### 4.4 What a run writes

`artifacts/runs/<timestamp>-<system>-<task>/`

| file | content |
|---|---|
| `manifest.json` | dataset id + hash, label source, split, slices, repeats, git sha (and dirty flag), chat model / effort / temperature / cache |
| `predictions.jsonl` | every prediction, per condition and repeat: label, rationale, resolved citations, tokens, latency |
| `evidence.jsonl` | every span handed to the classifier, per condition and item |
| `metrics.json` | everything in §5, machine-readable |
| `report.md` | the same as tables |

Quote nothing that cannot be traced to a run id, and record the run id next to the number in
`docs/graph-rag-notes/README.md`.

### 4.5 Answer-level RAG metrics

Faithfulness, answer relevance and context precision follow the RAGAS definitions and are implemented
in `gw_common/eval/rag_metrics.py` (not through the `ragas` package), so every intermediate judgement
is stored. They are scored **after** a run, from its directory:

```bash
uv run gw-eval --ragas artifacts/runs/<run_id>                       # all conditions, repeat 0
uv run gw-eval --ragas artifacts/runs/<run_id> --conditions cross_year_rrf --sample 100
uv run gw-eval --ragas artifacts/runs/<run_id> --ragas-export-check check.csv --ragas-n 50
uv run gw-eval --ragas artifacts/runs/<run_id> --ragas-score-check check.csv
```

| metric | how it is computed |
|---|---|
| faithfulness | the rationale is split into atomic statements; each is judged against the sources the classifier saw (`T`, `C`, `E1`…). Score = supported / total |
| answer relevance | three questions are generated back from the answer and compared, by embedding cosine, with the question actually asked; 0 if the answer is noncommittal. Absolute values depend on the embedding model; compare conditions, not against 1.0 |
| context precision | each retrieved passage is judged relevant or not to reaching the reference label; mean of precision@i over the relevant ranks. Undefined where nothing was retrieved (`sentence_only`, `local`) |
| context relevance | plain share of retrieved passages judged relevant |

Outputs land next to the run: `ragas.jsonl` (per answer: statements and verdicts, generated questions,
per-passage verdicts), `ragas.json`, `ragas.md`.

**The judge is an LLM, by default the same model that wrote the answers**, so it may be lenient.
`--ragas-export-check` writes a blind sheet (one row per statement and per passage, no judge verdict
shown) for a human to fill with Y/N; `--ragas-score-check` then reports agreement and Cohen's κ between
judge and human, including how often the judge said yes where the human said no. Quote the LLM-judged
numbers together with that agreement.

## 5. Metrics

**Primary:** macro-F1 over the three action labels, computed on rows whose gold label is an action
(796 on the full set, 331-split accordingly). This is A3CG's action-classification sub-task (AC) with
the gold aspect given; A3CG's published AC scores are a reference, not a like-for-like comparison.
Micro-F1 (pooled) is reported next to it because A3CG pools over pairs.

| block | metrics | why |
|---|---|---|
| action | macro-F1, micro-F1 (P/R), accuracy, per-label P/R/F1, confusion matrix | the task |
| detection | binary F1 for "row carries a valid aspect–action" (gold ≠ none) and `none` F1 | evidence can talk the model into inventing an aspect; this catches it |
| stability | mean ± sd over repeats, `unstable_items` (labels that changed between repeats), majority vote | the model re-samples; single runs mislead |
| comparison vs baseline condition | Δ macro-F1 (mean and vote), pooled flips wrong→right / right→wrong, McNemar on majority votes, bootstrap 95 % CI | is the delta bigger than the noise |
| slices | macro-F1 per row_type, aspect_source, agreement (unanimous vs split), category, gold | where the gain lands |
| evidence | coverage, mean spans, by source, `target_dropped` | did retrieval deliver anything |
| grounding | share of replies in the asked format, with a rationale, citing the target; `evidence_use_rate` (items with retrieved evidence that cite at least one span of it), share of shown spans cited, invalid refs | is the answer tied to sources, and does the classifier actually use what was retrieved |
| speed | per-call latency p50/p95, retrieval p50/p95, end-to-end per item, items/s (wall-clock throughput) | the course asks for latency and records per second |
| cost | input/output tokens per item, embedding tokens, USD per 1k items and per run (when prices are set), cached calls | the course asks for cost; cached calls are flagged because they are neither slow nor billed |
| retrieval (`--task retrieval`) | P@5, R@10, MRR, nDCG@10, wrong-company@10, by query type | needs pooled human judgements (§6.3) |
| answer-level RAG (`--ragas`) | faithfulness, answer relevance, context precision, context relevance (§4.5) | is the rationale supported by what was shown, and was what was retrieved relevant |

Re-running an identical configuration does not reproduce its macro-F1 exactly: the classifier
re-samples, and independent runs differ by a few points. **Do not compare systems by a difference of
means across runs; compare them with the paired McNemar on the same items** (the run directory keeps
per-item predictions for exactly this).

## 6. Plugging in your own RAG or classifier

Three ways, from most to least integrated. In every case the harness owns items, gold, metrics and
manifests; your code only answers *retrieve* and/or *classify*.

### 6.1 In-process system (recommended)

Create a workspace package, implement the Protocols in `gw_common/interfaces.py`, register an entry
point. `src/baseline-rag/` is the template.

```python
# src/my-rag/my_rag/__init__.py
from gw_common.classifiers.llm_action import LLMActionClassifier   # the shared classifier, or your own
from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query

class MyRetriever:
    def retrieve(self, query: Query, *, k: int = 10) -> list[EvidenceSpan]:
        # honour query.company, query.year_from/year_to, and skip query.anchor_year when
        # query.condition starts with "cross_year"; never return the target sentence
        ...

class MyRagSystem(BaseSystem):
    name = "my-rag"
    def supported_conditions(self):
        return [EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.LOCAL,
                EvidenceCondition.SAME_REPORT_RRF, EvidenceCondition.CROSS_YEAR_RRF]
    def retriever(self):  return MyRetriever()
    def classifier(self): return LLMActionClassifier()      # keep it shared unless the classifier IS your contribution

def build_system() -> MyRagSystem:
    return MyRagSystem()
```

```toml
# src/my-rag/pyproject.toml
[project]
name = "my-rag"
dependencies = ["gw-common"]
[project.entry-points."gw.systems"]
my-rag = "my_rag:build_system"
[tool.uv.sources]
gw-common = { workspace = true }
```

Add `src/my-rag` to `[tool.uv.workspace].members` in the root `pyproject.toml`, `uv sync`, then
`uv run gw-eval --list` shows `my-rag`.

The contract, in one table:

| object | fields you receive / must fill |
|---|---|
| `Query` (in) | `text`, `company`, `aspect`, `year_from`, `year_to`, `anchor_year`, `target_text`, `condition` |
| `EvidenceSpan` (out) | `statement_id` (your own id space), `text`, `company`, `year`, `page`, `file`, `score`, `why` (a short source tag, e.g. `bm25`, `rrf+rerank`, `graph:follows_up`) |
| `EvalItem` (in, classifier) | `item_id`, `text`, `aspect`, `category`, `company`, `year`, `page`, `context_prev`, `context_next` — **never the gold label** |
| `Prediction` (out, classifier) | `item_id`, `label`, **`rationale`** (why, in a sentence or two), **`citations`** (list of `Citation`), `evidence_ids`, optional `scores`, `parse_ok`, `invalid_citations`, `latency_ms`, `input_tokens`, `output_tokens`, `llm_calls` |
| `Citation` | `ref` (`T` target sentence, `C` neighbouring context, `E1`…`Ek` the k-th span shown), `statement_id`, `company`, `year`, `page`, `file`, `quote` — enough to open the page the claim rests on |

If you write your own classifier, read evidence from the `evidence` mapping (item_id → spans) and
respect the same budget (k = 3, 800 characters per span) or say in the notes that you did not. It must
return a `rationale` and the `citations` it rests on: a label without sources cannot be shown in the UI
or scored for faithfulness. `gw_common.classifiers.llm_action.resolve_citations` turns the tags a model
cites into `Citation` objects; the harness then reports the grounding block for you.

### 6.2 File exchange (no Python integration)

```bash
uv run gw-eval --export-queries queries.jsonl --conditions cross_year_rrf --split dev
# your code: for each line, retrieve and write {"item_id": ..., "spans": [{"text", "company", "year", "page"?, "statement_id"?, "score"?, "why"?}]}
uv run gw-eval --system baseline-rag --evidence evidence.jsonl --conditions cross_year_rrf --split dev --repeats 3
# or, if your system emits labels itself:
uv run gw-eval --system baseline-rag --predictions preds.jsonl --conditions cross_year_rrf --split dev
```

Exported queries carry no gold label. Evidence read back goes through the same target-sentence filter.
The `--system` given with `--evidence` only supplies the classifier; with `--predictions` it is ignored.

### 6.3 Retrieval-only evaluation

```bash
uv run gw-eval --task retrieval --system baseline-rag --queries queries.jsonl \
               --modes bm25,dense,rrf,rrf+rerank --export-pool pool.csv     # judging sheet: union of every mode's top-k
# fill `relevant` (0/1 or 0–3) -> qrels.jsonl {"query_id": ..., "relevant": {"<doc_id>": 1}}
uv run gw-eval --task retrieval --system baseline-rag --queries queries.jsonl --qrels qrels.jsonl
```

Queries: `{"query_id", "text", "company"?, "aspect"?, "anchor_year"?, "year_from"?, "year_to"?,
"condition"?, "type": company_claim | cross_year_aspect | generic}`. Judge the pool, not one system's
output, or the judged system wins by construction.

### 6.4 Serving

`uv run gw-serve --systems baseline-rag,graph-rag` exposes `/healthz`, `/systems`, `/classify`,
`/retrieve`, `/trajectory`, `/runs` (FastAPI, `gw_common/api/app.py`); the UI will sit on top of it.

## 7. Rules and caveats

1. **Dev for tuning, test once.** Anything you looked at while changing a prompt, threshold or
   retriever setting is dev. Test (669 rows) is opened once, for the numbers in the report.
2. **Repeats ≥ 3, cache bypassed.** The model re-samples; a cached run replays one answer and shows
   `unstable 0`, which is not stability. Report mean ± sd and the majority vote.
3. **Paired tests only across systems.** Cross-run noise on identical configurations is ~0.025
   macro-F1. `metrics.json` has McNemar on majority votes against the baseline condition; for two
   different systems compute it on the same items (see the notes for the recipe).
4. **Same classifier, same budget.** The RQ1 comparison is about retrieval. Changing the prompt,
   model, effort, k or the 800-character cap changes every arm; if you must, re-run every arm and say so.
5. **Never feed the gold.** `GoldItem.to_eval_item()` strips `gold_label`, `label_source`, `split`,
   `meta`; systems receive `EvalItem` only. Pre-annotations (`llm_pre_*`) are never inputs.
6. **Never return the target.** Retrievers should skip it; the harness drops it anyway and counts it.
7. **Provenance or it did not happen.** Every number in a document carries its run id, snapshot hash
   and, for retrieval, the passage-store hash.
8. **Keep the 34 human-filled rows out of the headline.** They are reported in the `aspect_source`
   slice and as an aspect-recall figure (17 % of no-aspect rows).
9. **Data handling.** Raw PDFs stay in `kb/raw/` and are never shared. The passage package is derived
    text for academic use inside the group. A3CG snapshots are for reference runs only (no licence file
    in the release); do not redistribute them.
10. **Commits.** One line, prefixed (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), one commit per finished
    step. Each line of work keeps its own experiment log under `docs/`, with run ids next to every number.
