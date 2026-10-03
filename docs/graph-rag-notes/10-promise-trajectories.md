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
| proposed outcome | achieved / failed / revised / unclear / disappeared | the fixed system model. Judge `v1`: the model names the outcome (`configs/prompts/promise_outcome.md`). Judge `v2` (default since §7): the model labels each evidence statement, a rule names the outcome (`promise_outcome_v2.md`) | `gw-graph promise-outcomes --judge v2 --repeats 3` |
| human check | blind sheet, 75 promises (round 1), 50 held-out promises (round 2) | `promise_ok`, `fields_ok`, `outcome` | `gw-graph promise-sheet`, then `gw-graph promise-score --sheet … [--outcomes …]` |

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
in the report:** one team member judged every row; a first pass was drafted with Codex (GPT family) and
used as the working interface, and the annotator reviewed it row by row and made the final call on each.
It counts as one human annotator's judgement with an AI-drafted first pass, not as several independent
annotators. Two things bound the anchoring risk: the system's proposed outcome was not on the sheet, and
the check disagrees with the system on 30 % of rows, always in the stricter direction.

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

Limits: one annotator, working from an AI-drafted first pass whose model family is the system's own;
14–16 rows per proposed class, so class-level precision carries wide intervals; table-only targets are
missing from the pool (section 2).

How loose the upper bound is was measured afterwards on the 11 rows the check labelled `disappeared`: a
keyword search over every statement of the company finds 5 of them in the reports
(`11-promise-case-studies.md` §3). The cases themselves are in that note.

## 7. Judge v2: the outcome is derived by rule from evidence-level labels (2026-10-03)

The problem, from §6: judge v1 gave a verdict on 21 of the 35 promises the check called `unclear`, and
its `failed` and `revised` verdicts held 53 % and 38 % of the time. The 22 disagreements fall into six
kinds: a result for another year read as the deadline year's (3); a different metric, level or scope
taken for this target, e.g. absolute withdrawal against an intensity target (7); an annual target set
again for the next year read as a moved deadline (4); a verdict inferred rather than stated (4); a
result for part of the commitment (1); a mention of the subject read as nothing at all (3).

### 7.1 Design

The model no longer names the outcome. For each evidence statement it answers three questions, and one
about the promise:

| label | values | question |
|---|---|---|
| `relation` | this_target / same_metric / other | is the statement about this very commitment (same metric, same scope, same level and baseline), about its metric only, or about something else? In doubt, same_metric |
| `deadline_result` | met / missed / none | does it state the result for the deadline year? Results of other years, progress, partial results and anything that needs inferring are none |
| `change` | later / none | is it itself a commitment or notice that gives this target a later or no date, or says it was postponed, extended, delayed or dropped? |
| `annual` (per promise) | true / false | is the promise a per-year performance level of the kind set again every year? |

`outcome.decide` then applies a fixed rule. A result or a change only counts on a `this_target`
statement.

1. a `met` and no `missed` → **achieved**
2. no `met`, a `later`, and the promise is not annual → **revised** (a moved goalpost explains a miss,
   so it precedes rule 3; for an annual target a later year is routine renewal and settles nothing)
3. no `met`, a `missed` → **failed**
4. otherwise, any `this_target` or `same_metric` statement → **unclear** (contradictory results end here)
5. otherwise → **disappeared**

A reply that does not label every statement is `unclear`. `annual` is true if either the model or the
extraction's `recurring` flag says so.

Grounding. `unclear` is the "not enough information" class of claim verification, which FEVER (Thorne et
al., NAACL 2018) keeps as a third label next to supported and refuted; making it the default is
abstention, which the survey of Wen et al. (TACL) describes as a means of reducing unsupported output.
Asking simple questions per piece of evidence and deriving the verdict from the answers is claim
decomposition (Chen et al., EMNLP 2022). The rule's order and the annual-target exception are ours
[project] and follow the human guide of §5 ("revised … without reporting the original as met"; renewal
is not revision).

### 7.2 Result on the round-1 sheet, used here as a development set

Same model (`gpt-5.6-luna`, low effort), same six evidence statements per promise as v1 and as the
annotator saw (`--evidence-from outcomes.jsonl`), n = 74.

| | v1 | v2 prompt, the model's own outcome (one run) | **v2, rule** (majority of 3 runs) |
|---|---|---|---|
| accuracy | 0.703 | 0.811 | **0.878** |
| Cohen's κ | 0.63 | 0.74 | **0.83** |
| over-commitment: a verdict where the check says unclear | 21 / 35 | 8 / 35 | **4 / 35** |
| under-commitment: unclear where the check has a verdict | 0 / 39 | 5 / 39 | 4 / 39 |
| verdicts that are right | 38 / 60 = 0.63 | 33 / 42 = 0.79 | **34 / 39 = 0.87** |

| precision, recall | v1 | v2, rule |
|---|---|---|
| achieved | 13/15, 13/14 | 12/13, 12/14 |
| failed | 8/15, 8/8 | 7/8, 7/8 |
| revised | 6/16, 6/6 | 5/7, 5/6 |
| unclear | 14/14, 14/35 | 31/35, 31/35 |
| disappeared | 11/14, 11/11 | 10/11, 10/11 |

- **Both parts contribute.** The middle column is the outcome the model states itself in the same reply,
  after labelling the evidence: the questions alone remove 13 of the 21 over-commitments, the rule
  removes 4 more. The rule's effect is on `revised`: over all 374 promises it turns 16 of the model's
  own `revised` into `unclear`, annual targets set again for the next year.
- **The price is 4 verdicts lost** (v1 lost none): two `achieved` the annotator inferred and the rule
  does not (a 5-star rating as proof of participation; "no significant fines" for "zero fines"), one
  `revised` that is an annual target renewed in a different form, which the rule cannot see by design,
  and one `disappeared`.
- **These are tuned-on numbers.** Three versions of the v2 prompt were tried against these 74 rows (one
  cached run each): (1) a `topic` relation and a per-statement moved/renewed choice: accuracy 0.703,
  over-commitment 9/35, but `disappeared` collapsed (10 of 11 became `unclear`); (2) three relations,
  `annual` asked once per promise: 0.865, 3/35; (3) one contradiction in the wording removed: 0.878,
  4/35. Iteration stopped there. A clean figure needs the held-out sheet of §7.4.

### 7.3 Stability, cost, and the distribution over all 374

The judge is not deterministic. Three uncached runs over the 374 promises agree pairwise on 89–91 % of
them; **56 promises (15 %) do not get the same outcome three times**, almost always a verdict against
`unclear` (achieved/unclear 25, disappeared/unclear 16, revised/unclear 8, failed/unclear 3). On the
development rows the three runs score 0.878, 0.878 and 0.919. The reported configuration is therefore
`--repeats 3`: strict majority, and no majority (2 promises) is `unclear`.

Cost: 1,122 calls, 1.55 M input and 0.55 M output tokens, USD 0.96 for the three runs (0.32 for one).

| outcome | v1 | v2 (majority of 3) | population estimate from the check (§6) |
|---|---|---|---|
| achieved | 153 (40.9 %) | 125 (33.4 %) | 36.0 % (27.9 – 42.1) |
| unclear | 134 (35.8 %) | 192 (51.3 %) | 48.7 % (40.0 – 58.0) |
| revised | 29 (7.8 %) | 22 (5.9 %) | 2.9 % (1.0 – 4.8) |
| failed | 33 (8.8 %) | 16 (4.3 %) | 4.7 % (2.4 – 7.1) |
| disappeared | 25 (6.7 %) | 19 (5.1 %) | 5.3 % (3.8 – 6.7) |

v2's raw shares now sit inside the check's intervals for four classes; `revised` is still above its
interval. This is a sanity check, not validation: the estimate comes from the same 74 labels. 204 of
the 374 promises are treated as annual (161 by the extraction's flag, 43 more by the model).

### 7.4 Held-out check (round 2, not yet filled)

`kb/annotation/spotchecks/promise_check_r2_20261003.xlsx`: 50 promises, 21 companies, none of them on
the round-1 sheet, drawn from the 299 remaining checkable promises by v2's outcome (all 8 `failed`, all
8 `disappeared`, 9 of 15 `revised`, 13 `achieved`, 12 `unclear`; seed 20261004). Same columns, same
guide and same evidence as round 1; the system's outcome is in the `.key.json` beside it, not on the
sheet. v1 and v2 disagree on 14 of the 50 rows.

```
gw-graph promise-sheet --judge v2 --limit 50 --seed 20261004 \
    --exclude-sheets kb/annotation/spotchecks/promise_check_20261003.xlsx \
    --out kb/annotation/spotchecks/promise_check_r2_20261003.xlsx
gw-graph promise-score --sheet kb/annotation/spotchecks/promise_check_r2_20261003.xlsx          # v2
gw-graph promise-score --sheet … --outcomes artifacts/graph/dev/promises/outcomes.jsonl          # v1
```

Because the sheet is stratified on v2's outcome, per-class precision can be read off directly; accuracy
and the over-commitment rate must be weighted by stratum size (achieved 112, unclear 156, revised 15,
failed 8, disappeared 8) before they are compared with v1.

### 7.5 What v2 does not fix

- **Evidence.** v2 judges the same six statements. The misses of `11-promise-case-studies.md` §3 (the
  right sentence not retrieved, target tables, a delay disclosed before the deadline year) are
  untouched: `unclear` and `disappeared` remain upper bounds.
- **Annual targets renewed at a weaker level** are read as renewal.
- **Scope the text does not settle.** "EMG Taiping" against "EMG Plant 2": the model took them for the
  same site and called the target missed; the annotator could not tell.
