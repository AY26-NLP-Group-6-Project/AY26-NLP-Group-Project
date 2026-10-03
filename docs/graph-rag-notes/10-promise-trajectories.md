# 10 · RQ2: dated commitments and what became of them

Started 2026-10-03. RQ1 showed that retrieval barely moves sentence-level classification (README §4k–4o),
so the graph line's case rests here: following a commitment across a company's reports is a join on
(company, target, year), not a similarity search. This is also what the supervisor asked to see
(fulfilled / unfulfilled promises with evidence, `08-promise-fulfilment-market-screen.md`).

## 1. Pipeline

| step | what | how | command |
|---|---|---|---|
| candidates | statements that mention a year not before their report year and a commitment cue | rule, recall-oriented | (inside the next two) |
| extraction | target span, metric, quantity, unit, baseline year, deadline year, kind, recurring | LLM under `configs/prompts/target_extraction.md`, then mechanical validation: the span must occur verbatim in the statement, the deadline must not precede the report year | `gw-graph targets` (in-repo, `gpt-5.6-luna`) or `gw-graph targets-export` → outside extractor → `gw-graph targets-ingest --source <tag>` |
| promises | restatements of one commitment across years merged; same-metric commitments with another deadline or quantity linked as `related` (a moved goalpost looks like this) | rule, deterministic | `gw-graph promises --source <tag>` |
| checkable | stated before its deadline; deadline ≤ 2025 and a report exists for the deadline year or the year after; metric names something | rule | (same) |
| evidence | statements of the deadline-year reports, tables included | BM25 over all statements + dense over prose sentences (`dev-sent`), RRF, top 6 | `gw-graph promise-outcomes` |
| proposed outcome | achieved / failed / revised / unclear / disappeared | LLM under `configs/prompts/promise_outcome.md`, the fixed system model | (same) |
| human check | blind sheet, 75 promises | `promise_ok`, `fields_ok`, `outcome` | `gw-graph promise-sheet`, then `gw-graph promise-score --sheet …` |

Grounding. A *promise with verifiable timing* is ML-Promise's notion (Seki et al., EMNLP 2025), narrowed
to commitments that name a deadline year. Outcome classes extend Jiang, Kim & Lu (Nature Climate Change
2025), who code emissions targets as achieved / failed / disappeared, with `revised` and `unclear`
[project]. Categories are A3CG's.

## 2. Extraction: two extractors on the same 3,164 candidates

Extraction is knowledge-base construction, done once, so the stronger reader is used for the store and
the in-repo small model is kept as the reproducible path and the comparison. The outcome proposal, by
contrast, is system output and stays on the fixed model.

| | `gpt-5.6-luna` (low effort, in-repo) | Claude sub-agents (12 shards, read by hand) |
|---|---|---|
| statements with a target | 1,215 | 995 |
| targets passing validation | 1,462 | 1,273 |
| rejected: span not verbatim | 163 | 0 |
| kinds (quantitative / milestone / qualitative) | 931 / 223 / 308 | 911 / 216 / 146 |
| marked recurring | 132 | 359 |
| targets dated to the report year itself | 283 | 218 |
| cost | 2.14 M input + 0.34 M output tokens, about USD 0.83 | about 1.9 M sub-agent tokens |

Statement-level agreement 0.905, Cohen's κ 0.79; on the 955 statements both extract from, the set of
deadline years matches in 893. The 260 statements only the small model extracts are mostly what the spec
excludes: "target | performance" rows where the year names the result column, results that mention a
target in passing, and regulatory deadlines. Its 163 rejections are stitched table cells. The sub-agents
were told to leave those out and reported the same borderline classes independently.

Known recall loss, by design: targets that sit in flattened tables with the year header, the metric and
the value in non-adjacent cells are not extracted (no contiguous span). Several issuers publish their
next-year targets only that way.

## 3. Promises (from the sub-agent extraction)

1,273 targets → **880 promises** (138 restated in more than one year; 50 companies). **374 are checkable**
inside the corpus (32 companies): 198 quantitative, 107 milestone, 69 qualitative; 161 are recurring
annual targets; deadlines 2021–2025 (45 / 71 / 92 / 79 / 87). Not checkable: 299 with a deadline after
2025, 171 stated in or after their deadline year, 35 with no report for the deadline year, 3 with a bare
anaphor as metric.

## 4. Proposed outcomes (system, unverified)

`gpt-5.6-luna` over the 374 checkable promises, 6 evidence statements each: achieved 153, unclear 134,
failed 33, revised 29, disappeared 25. **These are proposals, not findings**; nothing here is quoted
until the human sheet is scored.

One prompt rule was changed before any human label existed: a recurring annual target that is simply set
again for the next year was being called `revised` (30 of 63 `revised` proposals). The prompt and the
human guide now say that renewal is not revision; `revised` on recurring targets fell to 4.

## 5. Human check

`kb/annotation/spotchecks/promise_check_20261003.xlsx` (75 promises, 24 companies, at most 4 per company;
sampled with a floor per proposed outcome so rare classes are present: 14–16 of each). The system's
proposal is not on the sheet (`promise_sheet_key.json` holds it). Three judgements per row:

1. `promise_ok` — a genuine dated commitment by the company, deadline as extracted?
2. `fields_ok` — metric, quantity, unit, baseline right?
3. `outcome` — from the evidence shown: achieved / failed / revised / unclear / disappeared.

Scoring gives extraction precision, field accuracy, outcome agreement (accuracy, κ, per-class precision
and recall, confusion) and the human outcome distribution, which is the RQ2 descriptive result. Because
the sample is stratified by proposed outcome, the human distribution on the sheet is not the population
distribution; population estimates need the per-class agreement applied to the 374 proposals.

## 6. Result of the check (2026-10-03)

Sheet returned the same day, all 75 rows filled, every row with a written reason. **Provenance to state
in the report:** the folder holds a filling script and an annotation file, and several notes read "per
the user's ruling", so the judgements were drafted with an AI assistant and adjudicated by a team member
on the ambiguous rows. That makes this an LLM-assisted, human-adjudicated check, not six independent
annotators; it is described as such wherever the numbers are used.

| | |
|---|---|
| genuine dated commitment (`promise_ok`) | 74 / 75 = **0.987** |
| fields right (`fields_ok`) | 67 / 74 = **0.905** (errors: a dropped scope or condition, a quantity the statement does not give, a missing "zero") |
| outcome agreement, system vs check | accuracy **0.703**, Cohen's κ **0.63** (n = 74) |

| outcome | check | system precision | system recall |
|---|---|---|---|
| achieved | 14 | 0.87 | 0.93 |
| failed | 8 | 0.53 | 1.00 |
| revised | 6 | 0.38 | 1.00 |
| unclear | 35 | 1.00 | 0.40 |
| disappeared | 11 | 0.79 | 1.00 |

- **The system over-commits.** Every disagreement but one is a case the check calls `unclear` and the
  system gave a verdict on (10 as revised, 6 as failed, 3 as disappeared, 2 as achieved). It never says
  `unclear` where the check found a verdict. Typical causes, from the notes: a result from a later year
  read as the deadline year's result (13 training hours reported for 2025 scored against an FY2024
  target); "reduce to 15 %" read as "reduce by 15 %"; a related commitment with another deadline taken as
  proof of revision; evidence about a neighbouring topic (discrimination complaints for a privacy target).
- **When the system says `achieved` or `disappeared` it is usually right; `failed` and `revised` need a
  person.** Those two are the classes a reader cares most about, so the system's role is to shortlist,
  not to rule.

Because the sheet was sampled by proposed outcome, its raw mix is not the population mix. Weighting each
proposed class by its share of the 374 checkable promises (bootstrap 95 % CI over the sheet):

| outcome | estimated share of the 374 | 95 % CI |
|---|---|---|
| achieved | 36.0 % | 27.9 – 42.1 |
| unclear (mentioned, no verdict possible) | 48.7 % | 40.0 – 58.0 |
| disappeared | 5.3 % | 3.8 – 6.7 |
| failed | 4.7 % | 2.4 – 7.1 |
| revised | 2.9 % | 1.0 – 4.8 |
| not a promise after all | 2.4 % | 0.0 – 7.2 |

Reading: for about half of the dated commitments the company's own deadline-year report does not let a
reader tell whether the commitment was met; where it can be told, roughly three quarters were met, one
in ten missed, one in ten no longer mentioned, and one in twenty moved. This is on the evidence the
pipeline retrieved (6 statements from the deadline-year reports): an `unclear` or `disappeared` can also
mean retrieval missed the passage, so both are upper bounds on what the reports themselves leave open.

Limits: one checker and an LLM-assisted one; 14–16 rows per proposed class, so class-level precision
carries wide intervals; table-only targets are missing from the pool (section 2).
