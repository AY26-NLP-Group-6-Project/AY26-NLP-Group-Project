# Documentation

Start with the root `README.md`: setup, running an evaluation, plugging in a system. This folder holds
the reference and the record.

| file | what it is for |
|---|---|
| `evaluation.md` | what is evaluated and how: the data and its split, the evidence conditions, the metrics, what a run writes, the RAG metrics, publishing and comparing runs, the API |
| `baseline.md` | the ordinary-RAG arm every other arm is measured against, and the knowledge base it retrieves from: every statement, with the passage store as the granularity ablation |
| `graph.md` | the temporal claim graph: why, what is in it, how it is built, what aspect extraction and canonicalisation achieved, what the graph arms retrieve |
| `promises.md` | following dated commitments through later reports: extraction, the outcome judge, the evidence, the two human checks, the reporting convention |
| `agentic.md` | the agentic arm: what it does on each question, what it achieved on dev and why, the frozen test hypotheses and how to run them |
| `case-studies.md` | ten commitments followed page by page through the reports |
| `results.md` | the findings in one place, with what can and cannot be claimed |
| `history.md` | the dated log of every experiment, with run ids and the numbers as they were first measured |
| `evidence-ledger.md` | every design claim tagged cited, measured or assumed, with its source |
| `market-screen.md` | the literature screen on promise fulfilment and stock prices, and why that analysis is future work |
| `handoffs/` | the briefs given to outside annotators and extractors: aspect extraction, canonicalisation gold, the canonicalisation spot-check |
| `proposals/` | the course proposal and the alternatives, as submitted |

Published runs are under `results/`, one folder per system family and one subfolder per run, named
after what the run is. The human check sheets and their scores are under `kb/annotation/spotchecks/`.

Two conventions. Every number carries the run folder or sheet it comes from. `history.md` is dated and
append-only; the other files describe the current state and are rewritten when it changes.
