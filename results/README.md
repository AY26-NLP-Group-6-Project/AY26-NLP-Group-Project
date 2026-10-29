# Published runs

Small, shareable copies of evaluation runs (manifest, metrics, report; the per-item predictions stay in `artifacts/runs/`). One folder per system family, one subfolder per run, named after what the run is. Add one with `gw-eval --publish artifacts/runs/<run_id> --name <group>/<name> --note "..."`; compare two with `gw-eval --compare <dir_a> <dir_b>`.

The classifier column is the prompt style: `label` returns one word, `cited` a label with a rationale and citations; numbers across the two styles are not paired. The store column is what the retriever read (chunk store and its content hash, or the graph build). The run id is the local directory under `artifacts/runs/`.

| run | system | classifier | store | split | items | repeats | snapshot | best condition | vote macro-F1 | note | run id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [baseline/passage-hybrid-cited](baseline/passage-hybrid-cited/report.md) | baseline-rag | cited | `passages` c80d0ab23191 | dev | 331 | 3 | 3e18cc14e648 | sentence_only | 0.7580 | Hybrid retrieval over the passage store (18,839 windows of about 200 words, hash c80d0ab23191), cited classifier; the granularity ablation, paired against baseline/statement-hybrid-cited | `20261029T143243Z-baseline-rag-rq1` |
| [baseline/statement-hybrid-cited](baseline/statement-hybrid-cited/report.md) | baseline-rag | cited | `statements` d8a62bfe40c6 | dev | 331 | 3 | 3e18cc14e648 | cross_year_rrf | 0.7767 | Hybrid retrieval (BM25 + dense + RRF + rerank) over the statement store, every statement of five words or more (108,376, hash d8a62bfe40c6), cited classifier; the reference baseline, with the RAG metrics | `20261029T143225Z-baseline-rag-rq1` |
| [graph/graph-arms-cited](graph/graph-arms-cited/report.md) | graph-rag | cited | graph `dev` | dev | 331 | 3 | 3e18cc14e648 | cross_year_fused | 0.7668 | Graph and graph+BM25 fused retrieval over every statement of the parsed reports (graph build dev), cited classifier; paired against baseline/statement-hybrid-cited | `20261029T143232Z-graph-rag-rq1` |
