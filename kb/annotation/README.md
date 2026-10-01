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
