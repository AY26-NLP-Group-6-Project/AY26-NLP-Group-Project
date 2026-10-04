# Published runs

Small, shareable copies of evaluation runs (manifest, metrics, report). Add one with `gw-eval --publish artifacts/runs/<run_id> --note "..."`; compare two with `gw-eval --compare`.

| run | system | split | items | repeats | snapshot | best condition | vote macro-F1 | note |
|---|---|---|---|---|---|---|---|---|
| [20260929T150108Z-baseline-rag-rq1](20260929T150108Z-baseline-rag-rq1/report.md) | baseline-rag | dev | 331 | 3 | 23dc51f1d9de | local | 0.7640 | 4j passage-level hybrid baseline, label-style classifier |
| [20260929T152702Z-graph-rag-rq1](20260929T152702Z-graph-rag-rq1/report.md) | graph-rag | dev | 331 | 3 | 23dc51f1d9de | cross_year_fused | 0.7810 | 4j graph arms, label-style classifier (evidence cap 800) |
| [20260930T004540Z-baseline-rag-rq1](20260930T004540Z-baseline-rag-rq1/report.md) | baseline-rag | dev | 331 | 3 | 23dc51f1d9de | same_report_rrf | 0.7648 | 4k sentence-unit hybrid baseline, label-style classifier |
| [20260930T083207Z-baseline-rag-rq1](20260930T083207Z-baseline-rag-rq1/report.md) | baseline-rag | dev | 331 | 3 | 3e18cc14e648 | cross_year_rrf | 0.7804 | 4m sentence-unit hybrid baseline, cited classifier; RAG metrics in 4n |
| [20261002T053125Z-graph-rag-rq1](20261002T053125Z-graph-rag-rq1/report.md) | graph-rag | dev | 331 | 3 | 3e18cc14e648 | cross_year_fused | 0.7799 | 4o graph arms under the cited classifier; paired against 4m's sentence-unit baseline |
| [20261004T080206Z-baseline-rag-rq1](20261004T080206Z-baseline-rag-rq1/report.md) | baseline-rag | dev | 331 | 3 | 3e18cc14e648 | cross_year_rrf | 0.7722 | 4u all-statement store dev-stmt (no prose filter), cited classifier; paired against 4m |
