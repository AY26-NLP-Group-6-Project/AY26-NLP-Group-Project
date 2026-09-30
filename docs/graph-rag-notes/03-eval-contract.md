# 03 · Evaluation contract

The point of this file: **a system is anything that implements these Protocols and registers itself.**
The harness in `src/common` then evaluates it without knowing what is inside — RRF, graph traversal,
an agent, or a stub.

## 1. Protocols (`gw_common/interfaces.py`)

```python
class Retriever(Protocol):
    def retrieve(self, query: Query, *, k: int = 10) -> list[EvidenceSpan]: ...
    # Query carries: text, optional company, optional year window, optional aspect,
    # and `condition` in {local, same_report, cross_year}. Honouring the filters is the system's job.
    # `target_text` + `anchor_year` name the sentence being classified. A span from the same company-year
    # whose normalised text equals or contains it is the target itself (gw_common.evidence.is_target_span):
    # retrievers should skip it before cutting to k, and the harness drops any that slip through and
    # reports the count as `evidence.target_dropped`. Statement ids are system-specific, so the harness
    # never passes eval item ids as `exclude_statement_ids`.

class ActionClassifier(Protocol):
    def classify(self, items: Sequence[EvalItem], *, condition: EvidenceCondition,
                 evidence: Mapping[str, list[EvidenceSpan]] | None = None) -> list[Prediction]: ...
    # Prediction: {item_id, label in {implemented, planning, indeterminate, none},
    #              rationale: str, citations: list[Citation], evidence_ids: list[str],
    #              scores: dict[str, float] | None, parse_ok, invalid_citations,
    #              latency_ms, input_tokens, output_tokens, llm_calls}
    # Citation:   {ref: "T" | "C" | "E1".."Ek", statement_id, company, year, page, file, quote}
    #   A prediction names the sources its rationale rests on; the harness resolves nothing itself,
    #   it only measures: format ok, rationale present, evidence_use_rate, invalid refs.

class TrajectoryBuilder(Protocol):
    def trajectory(self, company: str, aspect: str, years: range) -> Trajectory: ...
    # Trajectory: ordered [{year, label, statement_id, page, metric?}] + transitions[]

class System(Protocol):          # what a package exports
    name: str
    def retriever(self) -> Retriever | None: ...
    def classifier(self) -> ActionClassifier | None: ...
    def trajectories(self) -> TrajectoryBuilder | None: ...
    def router(self) -> APIRouter | None: ...       # for gw-serve
```

Registration is by entry point, so nothing in `gw_common` imports a system:

```toml
# src/graph-rag/pyproject.toml
[project.entry-points."gw.systems"]
graph-rag = "graph_rag:build_system"
agentic-graph-rag = "graph_rag.agent:build_system"   # same package, different policy
```

A system may return `None` for tasks it does not support; the harness reports those as `n/a`
rather than failing.

## 2. Datasets

| id | content | label source | built by |
|---|---|---|---|
| `gw1000` | the 1,000 annotated sentences (ID, text, aspect, category, provenance) | `llm_pre` now, `human_majority` after the pilot | `gw_common.datasets.build_gw1000()` from `kb/annotation/GW_master_1000.csv` |
| `a3cg` | A3CG folds, for training and the sentence-only baseline | paper gold | existing dump in `tmp/data/a3cg` |
| `qrels50` | at least 50 retrieval queries x pooled top-10 judgements (3 query types) | human | later, M4 |
| `traj60` | about 60 (company, aspect) x 3+ year trajectories | human | later, M5 |

Snapshots are frozen to `data/eval/<id>.<label_source>.<hash>.jsonl`. The harness refuses to run
against an unfrozen dataset, and the hash is written into the run manifest.

`EvalItem` = `{item_id, text, aspect | None, category | None, company, year, page, context_prev,
context_next, gold_label, label_source}`. Systems receive everything **except** `gold_label`.

## 3. Tasks and metrics

| task | what it measures | primary metric | also reported |
|---|---|---|---|
| `rq1` | action classification under the seven evidence conditions | macro-F1 over implemented / planning / indeterminate, on rows whose gold is one of those | accuracy; per-condition delta vs `sentence_only`; flip analysis (wrong to right minus right to wrong); McNemar p; seen/unseen split via the A3CG fold mapping |
| `pairdet` | is there a valid aspect-action at all | binary F1 on `none` vs rest over all 1,000 rows | precision/recall, confusion |
| `retrieval` | evidence quality | nDCG@10 | P@5, R@10, MRR, **wrong-company@10** |
| `trajectory` | RQ2 | transition F1 | trajectory exact-match, per-transition confusion |
| `ops` | serving cost | latency p50/p95 (end to end, per item) | input/output tokens, LLM calls, tool calls, graph hops, cost multiplier vs the `same_report_rrf` arm |

The `ops` row is reported next to every accuracy number, never separately. Reference point from
arXiv 2601.07711: agentic pipelines cost about 3.3x input tokens, 1.9x output tokens and 1.5x wall
time versus a fixed enhanced pipeline, and latency is dominated by LLM calls. An agentic arm that
wins on F1 but costs 3x is a different verdict from one that wins for free, so both go in the table.

Rules:

- The `rq1` conditions are `sentence_only`, `local`, `same_report_rrf`, `cross_year_rrf`,
  `cross_year_graph`, `cross_year_fused` (graph + RRF) and `cross_year_agentic`. A system that only
  implements some of them reports the rest as `n/a`. The fused and agentic arms are required, not
  optional: the literature says graph-only loses to graph+vector (arXiv 2503.04338, EmeraldMind) and
  that agentic gains are conditional (arXiv 2601.07711).
- Metrics are computed **only** in `gw_common.eval.metrics`. A system that computes its own score
  does not get it into the report.
- Every run writes `artifacts/runs/<timestamp>-<system>-<task>/` containing
  `predictions.jsonl`, `metrics.json`, `manifest.json`, `report.md`.
- `gw-eval --compare A B` emits a side-by-side table plus a bootstrap 95 % CI on the primary metric.

## 4. Baselines that must stay runnable

1. `majority` — always the most frequent label. Sanity floor.
2. `sentence-only classifier` — the A3CG-fine-tuned encoder, no retrieval. The number everything
   else is compared against.
3. `baseline-rag` — BM25 + dense + RRF + reranker, same classifier, evidence conditions
   `local / same_report_rrf / cross_year_rrf`.
4. `graph-rag` — adds `cross_year_graph` and `cross_year_fused`.
5. `agentic-graph-rag` — adds `cross_year_agentic`: a bounded policy that may plan, rewrite the
   query and choose the next hop, with a hard cap of 3 hops and a per-request timeout. It reuses the
   same reranker as `baseline-rag`, because arXiv 2601.07711 finds agents worse than a reranker at
   picking the final documents.

If the graph arm does not beat `cross_year_rrf`, that is a result and it gets reported as one.

## 5. Label-source discipline

- Dev and iteration: `--labels llm_pre` (current default, about 86 % agreement with the two
  annotators who have finished so far).
- Anything quoted in the report: `--labels human`, re-run after the pilot, with `label_source`
  printed in the results table.
- `metrics.json` always carries `label_source`; `report.md` prints a warning banner when it is
  `llm_pre`.
