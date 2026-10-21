# kb/annotation — the gw1000 evaluation set

Versioned so every teammate scores the same 1,000 records with the same labels and split. The raw
reports the sentences come from stay in `kb/raw/` and are never committed.

| file | what |
|---|---|
| `eval.xlsx` | **the evaluation set.** Sheet `eval`: one row per record — `id, text, aspect, label`, then category, split, provenance, context, the six annotators' labels (pseudonymised as `A1`–`A6`), agreement, adjudication flag, three LLM pre-annotations and annotator notes. Sheet `README` describes every column; sheet `guide` is the annotation guideline (A3CG-aligned). No duplicate sentences |
| `eval.xls` | the same `eval` sheet in the legacy format and under the file name the course brief requires for submission. Generated, do not edit: `uv run gw-data export-xls` |
| `aspect_overrides.csv` | review trail for the 34 rows shown as *no aspect* that annotators still gave an action label: the span chosen, its source and a `Weak` flag. Already applied in `eval.xlsx` (`aspect_source = human_filled`) |
| `llm_notes.csv` | the three LLM pre-annotators' per-row label, aspect and rationale (3,000 rows). For label-noise analysis; never a system input |

Labels: `implemented`, `planning`, `indeterminate` (A3CG's three actions) and `none` (no valid
aspect–action). 417 / 191 / 222 / 170 rows. Split: dev 331 / test 669, stratified by row type × label ×
category; the 50 pilot rows, labelled by all six annotators, are in dev.

Agreement: 50 rows carry six labels (observed agreement 0.861, Fleiss' κ 0.809); the other 950 carry one.
`uv run gw-data build gw1000` recomputes these figures from the `A1`–`A6` columns.

## Human check sheets (`spotchecks/`)

| file | what |
|---|---|
| `ragas-check.csv`, `.result.json`, `ragas.summary.json` | the blind calibration of the RAG-metric judge (186 rows), its scoring and the judged run's summary |
| `promise-check-first-evidence.xlsx`, `.key.json`, `.result*.json` | the first RQ2 check: 75 promises on the first evidence; the key holds the system's proposals and the strata sizes; results for the first judge (`result.json`) and the rule-based judge on the same evidence (`result.v2*.json`) |
| `promise-check-trajectory.xlsx`, `.key.json`, `.result.json` | the held-out RQ2 check: 60 promises on the trajectory evidence, the final system |
| `promise-check-pair.xlsx`, `.key.json`; `promise-check-pair.annotator2.xlsx` | the two-annotator sheet: those 60 (earlier labels prefilled as Annotator 1) plus 90 random promises never checked; columns per annotator, adjudication and final; a second tab with the guide and live agreement. The `annotator2` file is the blind copy for a teammate |

Each sheet carries its guide on a second tab. Score a single-annotator sheet with
`gw-graph promise-score --sheet <xlsx>` and the two-annotator sheet with `gw-graph promise-pair-score`
(`docs/promises.md`).

## Changing it

Edit `eval.xlsx` (sheet `eval`) and rebuild; never edit the snapshots by hand.

```bash
uv run gw-data build gw1000          # -> data/eval/gw1000.<label_source>.<hash>.jsonl + gw1000.build_report.json
uv run gw-data export-xls            # refresh eval.xls
uv run gw-data describe gw1000 --split dev
```

A snapshot's hash is part of its filename and of every run manifest. Any edit changes the hash, so say
in the experiment log which runs used which hash. Adding a second annotator to more rows goes into the
next free `A` column of those rows; update `label`, `n_annotators` and `agreement` accordingly.

## De-identification

The annotators' original workbook is not kept in the repository. Annotators appear only as `A1`–`A6`
(the mapping is not stored), and names inside free-text notes were replaced by the same tags. Companies
are public issuers and are named.
