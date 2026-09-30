# kb/annotation — the gw1000 evaluation set

Versioned here so every teammate scores the same 1,000 items with the same labels and split. The
raw reports the sentences come from stay in `kb/raw/` and are never committed.

| file | what |
|---|---|
| `annotation.xlsx` | the annotators' workbook. Sheet `Master` is the source of truth: one row per sentence with one candidate aspect (or none), provenance, six annotator columns, the three LLM pre-annotations, majority, adjudication and `Final`. Other sheets (`IAA`, `LLM_Calc`, `LLM_Notes`, `Guide`) are the annotators' own working sheets and are not read by the pipeline. **Never edit `Master` by hand after this point**; changes go through the overrides file so they are auditable |
| `aspect_overrides.csv` | 34 rows that were shown as *no aspect* but received an action label: the annotators saw an aspect the proposer missed. Spans were reviewed on 2026-09-29 (`Proposed_Aspect`, `Category`, `Source`, `Weak`). Fill `Corrected_Aspect` / `Corrected_Category` to change one; the builder prefers those columns |

Rebuild the frozen snapshots after any change:

```bash
uv run gw-data build gw1000          # -> data/eval/gw1000.<label_source>.<hash>.jsonl + gw1000.build_report.json
uv run gw-data describe gw1000 --split dev
```

The builder (`gw_common/annotation.py`) recomputes Fleiss' κ from the annotator columns, assigns the
stratified dev/test split (pilot rows pinned to dev, seed 20260929) and writes one snapshot per label
source (`human_majority`, `llm_pre_claude`, `llm_pre_deepseek`, `llm_pre_gpt`). A snapshot's hash is
part of its filename and of every run manifest; if the hash in your `data/eval/` differs from the one in
git, you are not scoring the same data.

Annotator columns carry teammates' names; this repository is private to the group and the workbook is
not for redistribution.
