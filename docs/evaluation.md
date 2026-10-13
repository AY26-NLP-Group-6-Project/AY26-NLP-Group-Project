# Evaluation

A system is anything that implements two small Protocols (retrieve, classify) and registers itself.
The harness in `src/common` owns the data, the gold labels, the metrics and the run manifests; a
system only answers *retrieve* and *classify*. This file is the reference for that harness. The
promise-tracking task (RQ2) has its own pipeline and checks, described in `promises.md`.

## 1. The task

Given one sentence from a sustainability report and one candidate aspect (for example "Scope 3
emissions"), label the sentence **implemented / planning / indeterminate / none**, following the A3CG
scheme (Ong et al., ACL 2025). The question (RQ1) is whether evidence retrieved from the company's own
reports changes that label, and whether the change is for the better.

## 2. Data

`gw1000`: 1,000 sentences from 52 issuers' 2023–2025 reports, each with one candidate aspect and its
A3CG category (or none), page-level provenance and neighbouring sentences. Labels from six annotators:
the 50 pilot rows carry all six (Fleiss κ 0.809), the other 950 one each, one tie adjudicated. The
source workbook is `kb/annotation/eval.xlsx` (annotators pseudonymised); the frozen snapshot is
`data/eval/gw1000.human_majority.3e18cc14e648.jsonl`. The hash is part of the file name and of every run
manifest, so a changed annotation cannot be mistaken for the same data.

| slice | rows | note |
|---|---|---|
| aspect rows with an action label | 796 | the primary-metric population |
| aspect rows labelled `none` | 7 | the proposed aspect was rejected |
| no-aspect rows labelled `none` | 163 | |
| no-aspect rows with an action label | 34 | annotators saw an aspect the proposer missed; spans filled in by review (`kb/annotation/aspect_overrides.csv`), flagged `aspect_source=human_filled`; reported separately, never in the headline |

**Split: dev 331 / test 669**, stratified by row type × label × category, pilot rows pinned to dev.

| | dev | test |
|---|---|---|
| aspect / no-aspect rows | 266 / 65 | 537 / 132 |
| implemented / indeterminate / planning / none | 136 / 72 / 66 / 57 | 281 / 150 / 125 / 113 |

Tune on dev. Test is opened once, for the report; so far nothing has been run on it.

Label sources: `human_majority` (the gold), `llm_pre_{claude,deepseek,gpt}` (pre-annotations, for
label-noise analysis only; they agree with the human majority 0.79–0.80 and are never a system input),
`a3cg_gold` (A3CG's released test splits, reference only: their aspects are given, their statements
carry no provenance, and the release may be in the model's training data).

```bash
uv run gw-data build gw1000                 # kb/annotation/eval.xlsx -> snapshots + build report (κ, counts)
uv run gw-data export-xls                   # kb/annotation/eval.xls, the file name the course brief asks for
uv run gw-data describe gw1000 --split dev  # counts per slice
uv run gw-data build a3cg                   # A3CG test splits as action-classification snapshots
```

## 3. Evidence conditions

One classifier, one prompt (`configs/prompts/action_classifier_cited.md`); systems differ only in the
evidence they hand it: at most `k = 3` spans of at most 800 characters each.

| condition | evidence the classifier sees | who provides it |
|---|---|---|
| `sentence_only` | nothing (the A3CG setting; every delta is measured against it) | harness |
| `local` | the neighbouring sentences from the same page | harness |
| `same_report_rrf` | passages or sentences retrieved from the **same report** | the system's retriever |
| `cross_year_rrf` | retrieved from the **same company, other years** | the system's retriever |
| `cross_year_graph` | statements reached through the claim graph | graph-rag |
| `cross_year_fused` | graph first, BM25 over the company's other-year statements fills to k | graph-rag |
| `cross_year_agentic` | bounded plan–retrieve–stop loop | not built |

The harness drops any returned span that *is* the target sentence (same company and year, text equal
or containing it) and reports how many it dropped (`evidence.target_dropped`), so no arm can score by
re-reading the sentence it classifies.

## 4. Running

```bash
uv run gw-eval --list                                                       # registered systems
uv run gw-eval --system baseline-rag --split dev --repeats 3 \
               --conditions sentence_only,local,same_report_rrf,cross_year_rrf
uv run gw-eval --system graph-rag    --split dev --repeats 3 \
               --conditions sentence_only,local,cross_year_graph,cross_year_fused
uv run gw-eval --system graph-rag --split dev --slice row_type=aspect,category=workplace|management
uv run gw-eval --system graph-rag --split dev --sample 60 --repeats 1      # quick smoke test
```

Flags: `--split dev|test|all`; `--slice key=v1|v2,…` (keys: split, row_type, aspect_source, category,
company, year, pilot, has_aspect, gold, agreement, aspect_weak); `--sample N` (seeded); `--limit N`;
`--repeats N` (default 3; bypasses the LLM cache so each repeat re-samples the model); `--baseline`
(default `sentence_only`); `--k`; `--labels`; `--dataset`.

A run writes `artifacts/runs/<timestamp>-<system>-<task>/`:

| file | content |
|---|---|
| `manifest.json` | dataset id and hash, label source, split, slices, repeats, git sha and dirty flag, chat model, effort, temperature, cache, classifier style and prompt hash |
| `predictions.jsonl` | every prediction, per condition and repeat: label, rationale, resolved citations, tokens, latency |
| `evidence.jsonl` | every span handed to the classifier, per condition and item |
| `metrics.json` | everything in section 5, machine-readable |
| `report.md` | the same as tables |

## 5. Metrics

**Primary: macro-F1 over the three action labels**, on rows whose gold label is an action (796 on the
full set, 331 on dev). This is A3CG's action-classification sub-task with the gold aspect given; A3CG's
published scores are a reference, not a like-for-like comparison. Micro-F1 is reported next to it
because A3CG pools over pairs.

| block | metrics | why |
|---|---|---|
| action | macro-F1, micro-F1, accuracy, per-label P/R/F1, confusion matrix | the task |
| detection | binary F1 for "the row carries a valid aspect–action" and `none` F1 | evidence can talk the model into inventing an aspect; this catches it |
| stability | mean ± sd over repeats, items whose label changed between repeats, majority vote | the model re-samples; single runs mislead |
| against the baseline condition | Δ macro-F1 (mean and vote), pooled flips wrong→right / right→wrong, McNemar on majority votes, bootstrap 95 % CI | is the delta bigger than the noise |
| slices | macro-F1 per row type, aspect source, agreement, category, gold label | where a gain lands |
| evidence | coverage, mean spans, by source, target spans dropped | did retrieval deliver anything |
| grounding | replies in the asked format, with a rationale, citing the target; share of items that cite retrieved evidence; share of shown spans cited; invalid references | is the answer tied to sources, and is the retrieved text used at all |
| speed | per-call latency p50/p95, retrieval p50/p95, end to end per item, items per second | the course asks for latency and throughput |
| cost | input and output tokens per item, embedding tokens, USD per 1,000 items (when prices are set), cached calls | the course asks for cost; cached calls are flagged because they are neither slow nor billed |
| retrieval (`--task retrieval`) | P@5, R@10, MRR, nDCG@10, wrong-company@10, by query type | needs pooled human judgements (section 8) |
| answer-level RAG (`--ragas`) | faithfulness, answer relevance, context precision, context relevance | is the rationale supported by what was shown, and was what was retrieved relevant |

Re-running an identical configuration does not reproduce its macro-F1: independent runs differ by a
few points (three `sentence_only` votes on the same items: 0.7416 / 0.7591 / 0.7343). **Compare systems
with the paired McNemar on the same items**, never by a difference of means across runs.

## 6. Answer-level RAG metrics

Faithfulness, answer relevance and context precision follow the RAGAS definitions and are implemented
in `gw_common/eval/rag_metrics.py`, not through the `ragas` package, so every intermediate judgement is
kept. They are scored after a run, from its directory, by a judge model (the same `gpt-5.6-luna`):

```bash
uv run gw-eval --ragas artifacts/runs/<run_id>                                  # all conditions, repeat 0
uv run gw-eval --ragas artifacts/runs/<run_id> --conditions cross_year_rrf --sample 100
uv run gw-eval --ragas artifacts/runs/<run_id> --ragas-export-check check.csv --ragas-n 50
uv run gw-eval --ragas artifacts/runs/<run_id> --ragas-score-check check.csv
```

| metric | how |
|---|---|
| faithfulness | the rationale is split into atomic statements, each judged against the sources the classifier saw; supported / total |
| answer relevance | three questions generated back from the answer, compared by embedding cosine with the question asked; 0 if the answer is noncommittal. Compare conditions, not against 1.0 |
| context precision | each retrieved passage judged relevant to reaching the reference label; mean precision@i over relevant ranks. Undefined without retrieval |
| context relevance | share of retrieved passages judged relevant |

Outputs land next to the run (`ragas.jsonl`, `ragas.json`, `ragas.md`). The judge may be lenient, so
`--ragas-export-check` writes a blind sheet (no judge verdict shown) for a person to fill, and
`--ragas-score-check` reports agreement and Cohen's κ. Quote LLM-judged numbers with that agreement.
The one calibration done so far (`kb/annotation/spotchecks/ragas-check.*`) found the judge strict on
faithfulness and lenient on context relevance by a factor of about 1.7; see `results.md`.

## 7. Publishing and comparing

```bash
uv run gw-eval --publish artifacts/runs/<run_id> --name baseline/<what-it-is> --note "one line"
uv run gw-eval --compare results/baseline/sentence-hybrid-cited results/graph/graph-arms-cited
```

`--publish` copies the manifest, metrics and report (not the per-item files) into `results/<group>/<name>/`
and regenerates `results/README.md`. `--compare` pairs the two runs' majority votes on the items both
scored and reports flips and McNemar p per condition; it refuses runs on different snapshots.

## 8. Plugging in a system

### In-process (recommended)

Create a workspace package, implement the Protocols in `gw_common/interfaces.py`, register an entry
point. `src/example-rag/` is a copy-me template; `src/baseline-rag/` the real thing.

```python
# src/my-rag/my_rag/__init__.py
from gw_common.classifiers.llm_action import LLMActionClassifier   # the shared classifier, or your own
from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query

class MyRetriever:
    def retrieve(self, query: Query, *, k: int = 10) -> list[EvidenceSpan]:
        # honour query.company and query.year_from / year_to; skip query.anchor_year when
        # query.condition starts with "cross_year"; never return the target sentence
        ...

class MyRagSystem(BaseSystem):
    name = "my-rag"
    def supported_conditions(self):
        return [EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.LOCAL,
                EvidenceCondition.SAME_REPORT_RRF, EvidenceCondition.CROSS_YEAR_RRF]
    def retriever(self):  return MyRetriever()
    def classifier(self): return LLMActionClassifier()   # keep it shared unless the classifier is your contribution

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

Add `src/my-rag` to `[tool.uv.workspace].members` in the root `pyproject.toml`, `uv sync`, and
`uv run gw-eval --list` shows `my-rag`.

| object | fields |
|---|---|
| `Query` (in) | `text`, `company`, `aspect`, `year_from`, `year_to`, `anchor_year`, `target_text`, `condition` |
| `EvidenceSpan` (out) | `statement_id` (your own id space), `text`, `company`, `year`, `page`, `file`, `score`, `why` (a short source tag: `bm25`, `rrf+rerank`, `graph:follows_up`) |
| `EvalItem` (in, classifier) | `item_id`, `text`, `aspect`, `category`, `company`, `year`, `page`, `context_prev`, `context_next`; never the gold label |
| `Prediction` (out, classifier) | `item_id`, `label`, `rationale`, `citations` (list of `Citation`), `evidence_ids`, optional `scores`, `parse_ok`, `invalid_citations`, `latency_ms`, `input_tokens`, `output_tokens`, `llm_calls` |
| `Citation` | `ref` (`T` the target sentence, `C` the context, `E1`…`Ek` the k-th span shown), `statement_id`, `company`, `year`, `page`, `file`, `quote` |

A classifier of your own reads evidence from the `evidence` mapping (item id → spans), keeps the same
budget (k = 3, 800 characters per span) or says so, and returns a `rationale` and the `citations` it
rests on: a label without sources cannot be shown in the UI or scored for faithfulness.
`gw_common.classifiers.llm_action.resolve_citations` turns cited tags into `Citation` objects.

### File exchange

```bash
uv run gw-eval --export-queries queries.jsonl --conditions cross_year_rrf --split dev
# for each line, retrieve and write {"item_id": ..., "spans": [{"text", "company", "year", "page"?, "statement_id"?, "score"?, "why"?}]}
uv run gw-eval --system baseline-rag --evidence evidence.jsonl --conditions cross_year_rrf --split dev --repeats 3
# or, if your system emits labels itself:
uv run gw-eval --system baseline-rag --predictions preds.jsonl --conditions cross_year_rrf --split dev
```

Exported queries carry no gold label. Evidence read back goes through the same target-sentence
filter. With `--evidence` the `--system` only supplies the classifier; with `--predictions` it is ignored.

### Retrieval only

```bash
uv run gw-eval --task retrieval --system baseline-rag --queries queries.jsonl \
               --modes bm25,dense,rrf,rrf+rerank --export-pool pool.csv     # judging sheet: union of every mode's top-k
# fill `relevant` (0/1 or 0–3) -> qrels.jsonl {"query_id": ..., "relevant": {"<doc_id>": 1}}
uv run gw-eval --task retrieval --system baseline-rag --queries queries.jsonl --qrels qrels.jsonl
```

Queries: `{"query_id", "text", "company"?, "aspect"?, "anchor_year"?, "year_from"?, "year_to"?,
"condition"?, "type": company_claim | cross_year_aspect | generic}`. Judge the pool, not one system's
output, or the judged system wins by construction. No qrels have been collected yet.

## 9. Serving

`uv run gw-serve --systems baseline-rag,graph-rag` exposes one FastAPI app with one router per system
(`gw_common/api/app.py`), so a front end can switch systems with a parameter:

```
GET  /healthz       {status, git_sha, systems, graph_build_id}
GET  /systems       [{name, capabilities: {retrieve, classify, trajectory}}]
POST /classify      {text, company?, year?, aspect?, condition, system} -> {label, scores, evidence, latency_ms}
POST /retrieve      {query, company?, year_from?, year_to?, k, condition, system} -> {hits, latency_ms}
GET  /trajectory    ?company=&aspect=&from=&to=&system= -> {points, transitions}
GET  /graph/subgraph ?company=&aspect=&hops=2 (graph-rag only) -> {nodes, edges}
GET  /runs          evaluation runs with their metrics
```

Request and response models are the pydantic models of `gw_common.schemas`; routes hold no logic;
every response that shows text carries `{company, year, page}`. No front end has been built.

## 10. Rules

1. **Dev for tuning, test once.** Anything looked at while changing a prompt, threshold or retriever
   setting is dev.
2. **Repeats ≥ 3, cache bypassed.** A cached run replays one answer and shows no instability, which is
   not stability. Report mean ± sd and the majority vote.
3. **Paired tests across systems.** Cross-run noise on identical configurations is about 0.025 macro-F1.
4. **Same classifier, same budget.** The retrieval comparison holds the prompt, model, effort, k and
   the 800-character cap fixed; changing any of them changes every arm, so re-run every arm and say so.
5. **Never feed the gold.** `GoldItem.to_eval_item()` strips the label, the label source, the split and
   the metadata; pre-annotations are never inputs.
6. **Never return the target.** Retrievers should skip it; the harness drops it anyway and counts it.
7. **Provenance.** Every number in a document carries its run folder, snapshot hash and, for retrieval,
   the store hash.
8. **The 34 human-filled rows stay out of the headline.** They are reported in the `aspect_source` slice.
