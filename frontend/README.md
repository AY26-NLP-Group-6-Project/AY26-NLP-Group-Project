# Demo front end

A Streamlit page that runs one item of a research question's dev split through one registered
system, step by step, and shows the answer against the gold. It is the "simple, friendly UI for
querying" the course brief asks for, over the same code the evaluation runs (`docs/evaluation.md`).

```bash
uv sync --group frontend                 # adds Streamlit to the workspace environment
uv run streamlit run frontend/app.py     # opens http://localhost:8501
```

It needs what an evaluation run needs: `.env` with the chat and embedding keys, the statement store
under `artifacts/baseline/statements/` (every system) and the graph under `artifacts/graph/dev/`
(`graph-rag`). Page previews need the raw reports under `kb/raw/`, which are never shared; without
them the preview says so and everything else works.

## What is on the page

| where | what |
|---|---|
| sidebar | the research question (RQ1 · label a sentence / RQ2 · follow a promise) and its definition; the system, the evidence condition, `k`, the number of model runs to vote over, whether to replay cached model responses; the setup (model, effort, prices, knowledge-base counts and hash, git) |
| query card | one item drawn at random from the dev split: for RQ1 the sentence with its company, year, page, aspect and neighbouring sentences; for RQ2 the commitment with its metric, deadline and the report years the retriever may read. **🎲 Another one** draws again; an id (`42`, `P00042`) jumps to an item; a toggle lets you type a query of your own (no gold label then) |
| **▶ Run with this query** | the steps as they happen, each with a live timer: loading the system (the first use reads the store, a few seconds to a minute), retrieval, then the shared classifier (RQ1) or the shared judge (RQ2), once per run |
| the answer | **correct / wrong** against the gold, the vote over runs when there are several; retrieval, generation and end-to-end time, tokens, embedding tokens and cost; the rationale and the sources it cites; every evidence span shown to the model, with where it came from (`why`), cited ones pinned; for RQ2 the evidence as a timeline by report year with the judge's label on each statement (this target / same metric, deadline met / missed, moved later) |
| the gold's context | RQ1: the label source, how many annotators, their agreement, the pre-annotations (never an input); RQ2: both annotators' outcomes and notes, whether they agreed, the adjudication |
| page preview | any cited source opened at its page in the raw report, with the URL it was fetched from |
| session log | every run with its timings, tokens and cost; a CSV download; the course's "five queries and their speed" |
| published runs | the conditions of every run under `results/` for the task, from the evaluation harness |

## Rules it follows

The same as the harness. The system never sees the gold label (`GoldItem.to_eval_item()`); the target
sentence is dropped from the evidence (`gw_common.evidence.drop_target`) and the drop is reported;
the RQ1 classifier and the RQ2 judge are the shared ones, with the same prompts and the same `k`
by default (3 and 20). With "Replay cached model responses" off (the default) every run calls the
model afresh, so a timing is a real timing and two runs can disagree; on, a request already in
`artifacts/cache/llm.sqlite` is answered from there, offline and instantly. The numbers on this page
are one item's; the numbers to quote are in `docs/results.md`, from runs with repeats and paired tests.

## Files

| file | what |
|---|---|
| `app.py` | the Streamlit page |
| `core.py` | what it runs, with no Streamlit in it: the dev split, the systems, the steps, pages, published runs |
| `../tests/test_frontend.py` | the core helpers, with a fake system |
