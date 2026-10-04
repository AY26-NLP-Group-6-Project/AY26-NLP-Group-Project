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
| evidence | mode `deadline` (first version, §4–7): statements of the deadline-year reports, BM25 over all statements + dense over prose sentences (`dev-sent`), RRF, top 6. Mode `trajectory` (default since §8): every report after the promise up to the year after the deadline, both rankings over all statements, a budget per report year, neighbours of the best hits, linked targets | `gw-graph promise-evidence --evidence trajectory` |
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
(How loose: §8. The first retrieval hardly ever showed the sentences that carry results; on complete
evidence the human-verified `unclear` share is 31 %, not 49 % (§8.6). The figures of this section
describe the first evidence. Weighted to the 374, v1 was right 82 % of the time and gave a verdict on
31 % of the promises the check calls unclear; the raw rates above are those of the stratified sheet.)

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

### 7.4 Held-out check: drawn, then withdrawn

A round-2 sheet of 50 held-out promises was drawn on this judge and this evidence (commit `a5e2bf9`).
It was never filled: the evidence changed before anyone judged it (§8), and labels given "from the
evidence shown" would not have carried over. It is removed; the held-out check is the round-3 sheet of
§8.5, drawn on the final system.

### 7.5 What v2 does not fix

- **Evidence.** v2 judges the same six statements. The misses of `11-promise-case-studies.md` §3 (the
  right sentence not retrieved, target tables, a delay disclosed before the deadline year) are
  untouched: `unclear` and `disappeared` remain upper bounds.
- **Annual targets renewed at a weaker level** are read as renewal.
- **Scope the text does not settle.** "EMG Taiping" against "EMG Plant 2": the model took them for the
  same site and called the target missed; the annotator could not tell.

## 8. Trajectory evidence: the promise followed through every later report (2026-10-03)

### 8.1 Why the first evidence missed the answers

`11-promise-case-studies.md` §3 found by hand that 5 of 11 `disappeared` promises were in the reports
after all, and named three causes. Ranking the hand-found answer statements under the first retrieval
shows one mechanism behind most of them:

| promise | answer statement | BM25 rank | dense rank | fused rank (cut at 6) |
|---|---|---|---|---|
| P00761 ThaiBev solar rooftops | "installed solar rooftops at two distribution centers" | 1 | no vector | 7 |
| P00347 Jumbo complaints | FY2022 performance table | 1 | no vector | 9 |
| P00268 Gallant GHG | "achieved a 15.4% reduction in GHG emissions" | 3 | no vector | 16 |
| P00461 Old Chang Kee electricity | "was 61 kwh per square foot (FY2020: 68 …)" | 3 | no vector | 18 |
| P00323 Indofood ISPO | "by 2024 has been postponed" | 5 | 11 | 7 |
| P00472 Old Chang Kee accidents | "Requires improvement as we recorded two cases" | none | 10 | 19 |
| P00811 Tiong Woon ERP | "In FY2022, we began integrating …" | none | 58 | not ranked |
| P00329 Indofood pouch | "has been delayed" (2023 report, deadline 2025) | 1 | 1 | outside the window |

Dense retrieval ran over the shared sentence store (`dev-sent`), which holds the statements that pass
the prose filter of RQ1: 71,342 of 110,314. The 35 % it leaves out are not only tables: a sentence with
figures fails the filter's letter ratio, a sentence without one of its listed verbs fails its verb test.
Result sentences are exactly these. A statement outside the store could score in one of the two fused
rankings only, and RRF (k = 60) then puts a statement ranked first in one list (1/61 = 0.0164) below one
ranked thirtieth in both (2/90 = 0.0222). The effect on what the judge saw: **of the 2,244 statements
shown under the first evidence, 37 (1.6 %) came from outside the sentence store.** The half of the
commitments that §6 found "unclear" were judged almost entirely without the sentences that carry
results.

### 8.2 Design (`promises/evidence.py`, mode `trajectory`)

1. **Two complete rankings.** Every statement of a report is ranked by BM25 and by dense similarity;
   vectors the sentence store lacks are embedded on demand and cached (23,089 statements, once). RRF
   then fuses rankings over the same documents.
2. **A budget per report year**, over every report after the one that made the promise up to the year
   after the deadline: 6 statements from the first report at or after the deadline, 3 from the next,
   2 from each earlier one.
3. **Neighbours.** The statements directly before and after the two best hits of the deadline report
   are added, whatever their length or rank. A target table is parsed into one statement per cell; the
   result sits beside the target and shares no words with it.
4. **Linked targets.** Targets the extractor attached to the promise as `related` (same company, same
   metric key, another deadline or level), first stated inside the window, are added whatever their
   rank: at most 3.
5. **Order and adjacency.** Statements are shown in report order, and one that comes right after the
   previous one in the report is marked "directly follows E3", so a target cell and its result are read
   together.

The outcome rule keeps to the calendar now that earlier reports are shown (`outcome.decide`): a report
older than the deadline year cannot establish a miss, nor an annual target's deadline-year result; it
can establish a deliverable finished early or a moved deadline; and a commitment repeated before its
deadline and not mentioned from the deadline year on is `disappeared`. The human guide says the same.
The judge prompt gained four clarifications the new evidence made necessary (the "directly follows"
mark; a target cell is not a result; the columns of a flattened row; a bare "this target"), added in two
rounds while looking at round-1 rows only. The last two did not remove the errors they were written for
(§8.4).

The budgets, the neighbour rule and the calendar rules are ours [project]. Nothing here uses the aspect
nodes of the graph: they cover 29,637 statement mentions, not all 110,314 statements. The join that is
used is the promise graph's own (`related`), and it turned out to matter little: 153 related targets
fall inside the windows of 110 promises, and per-year retrieval had already found 143 of them.

### 8.3 Checks that need no new labels

| check | first evidence | trajectory |
|---|---|---|
| statements per promise | 6 | 11.6 (max 19), from 2.0 report years |
| share from outside the sentence store | 1.6 % | 42 % |
| hand-found answer statements shown (8) | 0, by construction | **6** |
| round-1 verdict rows whose cited statements are all still shown (28) | 28 | 26 (at least one: 28) |

The six recovered: four through the complete rankings (they now rank first or second in their report),
one through the wider window (the 2023 delay notice for a 2025 target), one as a neighbour (the result
cell beside the accident-frequency target, itself ranked 26th). The two not recovered: the Indofood
postponement sentence ranks 8th in a report with many ISPO statements, and the Tiong Woon sentence is
not reachable by similarity at all. Of the trajectory evidence, 3,301 statements are retrieved, 1,019
are neighbours and 10 come from the link alone.

### 8.4 What the judge says on the new evidence (system output, unverified)

Judge v2, final prompt, majority of three runs, same model; only the evidence differs.

| outcome | first evidence | trajectory evidence |
|---|---|---|
| achieved | 114 (30.5 %) | 173 (46.3 %) |
| unclear | 200 (53.5 %) | 135 (36.1 %) |
| revised | 19 (5.1 %) | 29 (7.8 %) |
| failed | 16 (4.3 %) | 27 (7.2 %) |
| disappeared | 25 (6.7 %) | 10 (2.7 %) |

132 of the 374 promises change outcome: 99 go from `unclear` or `disappeared` to a verdict (71
achieved, 16 failed, 12 revised), 19 lose one. The verdicts rest on 365 statements: 352 retrieved, 12
neighbours, 1 linked; 312 from the deadline-year report, 40 from the year after, 13 from earlier
reports. So the gain is mostly the first design point, complete rankings inside the report where the
outcome belongs; the wider window and the neighbours each decide a handful (6 verdicts rest only on
earlier reports, 4 only on neighbours).

On the round-1 sheet the same judge with the first evidence scores 0.919 (κ 0.88, over-commitment 2/35,
verdicts right 35/38), so the prompt clarifications did not cost anything there. Its labels cannot
score the trajectory run, since the annotator saw six other statements, but they show the direction:

| check on the first evidence | system on trajectory evidence |
|---|---|
| achieved (14) | achieved 12, unclear 2 |
| failed (8) | failed 5, revised 2, unclear 1 |
| revised (6) | revised 3, achieved 3 |
| unclear (35) | achieved 14, failed 5, revised 2, unclear 14 |
| disappeared (11) | disappeared 6, failed 2, achieved 1, revised 1, unclear 1 |

Seven of the eight hand-checked promises of §8.1 now get the outcome the full reading in note 11 gave
them (ThaiBev's two-of-four delivery as `unclear`). For the eighth the system found what the hand search
had not: Tiong Woon's 2022 report says "The first phase of the project successfully "went-live" on 1
July 2022", against a launch promised for the first half of 2022, and the outcome is `failed`: literal,
and one day late.

Reading the new evidence of ten changed round-1 rows (not blind, one reader): the seven that moved from
`unclear` to a verdict hold, e.g. "There were no non-compliances in FY2022", a training average of 41
hours against a 26-hour target. Of three whose verdict changed, one follows the rule (allergen
disclosure: missed and re-dated, so `revised`) and two show error types that are new and not fixed:

- **A flattened multi-column row read across columns.** CDL HTrust's 2024 table runs "Targets for FY
  2024 | Key results in FY 2024 | Targets for FY 2025"; the model took next year's target
  ("Decarbonisation target validated with SBTi") for a result and the rule returned `achieved`, although
  later statements still plan the target. This is over-commitment in a new place: complete retrieval
  brings in the tables the first evidence never showed.
- **A bare "this target".** Old Chang Kee's "We have achieved this target for FY2022.", from another
  page, was taken for the electricity target; against the explicit miss on the right page the two
  results cancel to `unclear`.

Instability is unchanged: 50 of 374 promises do not get the same outcome three times (53 on the first
evidence). Cost: USD 1.49 for the three runs (2.27 M input, 0.87 M output tokens), against 1.04.

**What this does to the RQ2 finding.** §6 estimated that for 49 % of dated commitments the company's
own reports do not let a reader tell the outcome. Much of that was the retrieval: with the result
sentences in view the system's `unclear` share is 36 %, and `disappeared` falls from about 6 % to under
3 %. These are system outputs. The §6 figures stay the only human-verified ones, they describe what the
first evidence showed, and they should not be quoted as a property of the reports.

### 8.5 Held-out check (round 3, to be filled)

`kb/annotation/spotchecks/promise_check_r3_20261003.xlsx`: 60 promises from 23 companies, none on the
round-1 sheet (the rows every prompt version was tried on), drawn from the 299 other checkable promises
by the system's outcome: failed 14 of 15, revised 13 of 21, disappeared 4 of 4, achieved 14 of 143,
unclear 15 of 116; at most 4 per company; seed 20261005. Evidence is the trajectory evidence, 11.7
statements per row, grouped by report year with the deadline year marked. The system's outcome is in
the `.key.json` beside the sheet, not on it.

```
gw-graph promise-evidence --evidence trajectory
gw-graph promise-outcomes --judge v2 --evidence trajectory --repeats 3
gw-graph promise-sheet --judge v2 --evidence trajectory --limit 60 --seed 20261005 \
    --exclude-sheets kb/annotation/spotchecks/promise_check_20261003.xlsx \
    --out kb/annotation/spotchecks/promise_check_r3_20261003.xlsx
gw-graph promise-score --sheet kb/annotation/spotchecks/promise_check_r3_20261003.xlsx
```

The sheet is stratified on the system's outcome: per-class precision reads off directly; accuracy, the
over-commitment rate and the outcome shares of the 299 need the strata weighted by their sizes above.
`promise-score` now does that weighting itself (`population` in its output; the strata sizes are kept in
the sheet's key).

### 8.6 Result of the held-out check (2026-10-03)

Sheet returned the same day, all 60 rows judged. **Provenance:** as in round 1, one team member, working
through a Codex-drafted first pass; 17 notes record a point the annotator settled personally ("user
confirmed"). The dump the drafting tool worked from holds the sheet's own columns only; the system's
outcomes are in a separate key file and were not on the sheet.

Raw rates on a sheet that over-samples rare outcomes describe no population, so the comparison is on
the weighted estimates (95 % bootstrap intervals). Round 1 is re-read the same way; §6 gave its raw
rates only.

| | round 1: judge v1, first evidence | **round 3: judge v2, trajectory evidence, held out** |
|---|---|---|
| sheet, pool | 75 of 374 | 60 of 299 |
| raw accuracy, κ | 0.703, 0.63 | 0.667, 0.57 |
| accuracy, weighted | 0.82 (0.72 – 0.90) | 0.80 (0.68 – 0.90) |
| … with failed and revised as one class | 0.82 (0.72 – 0.90) | 0.83 (0.71 – 0.93) |
| **over-commitment**: a verdict where the check says unclear | 31 % (20 – 42) | **8 % (3 – 15)** |
| under-commitment: unclear where the check has a verdict | 0 % | 15 % (4 – 24) |
| verdicts that are right | 75 % (63 – 86) | 84 % (71 – 93) |
| genuine commitment / fields right | 0.987 / 0.905 | 1.000 / 0.817 |

- **The over-commitment fix holds on rows no prompt was tuned on**: 8 % against 31 %, intervals apart.
- **Overall accuracy did not move.** v1 was right 82 % of the time because it said `unclear` often and
  was right when it did (14 of the 15 sampled); v2 on complete evidence says `unclear` less and is right
  80 % of the time. What changed is what the system is willing and able to say, below.
- The price of the stricter judge is real on held-out rows: 15 % of the promises the check settles are
  left `unclear`.

**What became of the promises, human-verified.** Estimated shares of dated commitments, each sheet
weighted to its pool:

| outcome | first evidence (round 1) | **complete evidence (round 3)** |
|---|---|---|
| achieved | 36.0 % (27.9 – 42.1) | **50.1 % (40.7 – 58.7)** |
| unclear | 48.7 % (39.8 – 57.7) | **30.9 % (21.9 – 39.0)** |
| not met: failed or revised | 7.6 % (4.7 – 10.5) | **12.8 % (7.9 – 20.5)** |
| … failed | 4.7 % | 2.9 % |
| … revised | 2.9 % | 9.9 % |
| disappeared | 5.3 % (3.8 – 6.7) | 6.2 % (0.7 – 13.9) |
| not a promise | 2.4 % | 0 % |

The annotator, shown the complete evidence, could not tell the outcome for 31 % of commitments, not 49 %.
That is consistent with §8.4: about a third of the earlier `unclear` was the retrieval. Where the
outcome can be told, four in five commitments were met (50.1 of 62.9) and one in five was missed or
re-dated. `disappeared` did not fall as the system's own count suggested (§8.4: 2.7 %): the
annotator calls `disappeared` some rows the system leaves `unclear`, and the interval is wide.

**By the outcome the system proposed** (what a reader of the system's output can rely on):

| system says | pool | sampled | check agrees | otherwise |
|---|---|---|---|---|
| achieved | 143 | 14 | 13 | 1 revised |
| unclear | 116 | 15 | 11 | 2 achieved, 2 disappeared |
| revised | 21 | 13 | 8 | 2 unclear, 2 failed, 1 achieved |
| failed | 15 | 14 | 5 | 6 revised, 3 unclear |
| disappeared | 4 | 4 | 3 | 1 unclear |

`achieved` can be relied on. `failed` and `revised`, read as one class, are right 21 times in 27, and
miss one of 22; told apart they are not reliable, which is the largest block of the 20 disagreements:

| kind of disagreement | rows | |
|---|---|---|
| failed against revised | 8 | 6 the check calls revised, the system failed; 2 the other way |
| a verdict where the check says unclear | 6 | 3 failed (a scope or column the text does not settle: Riverstone's target table twice, "graduates and current students" against 300 graduates), 2 revised, 1 disappeared |
| unclear where the check has a verdict | 4 | 2 achieved the annotator inferred (a director under 50 on the board; "no significant fines"), 2 disappeared |
| achieved against revised | 2 | a changed metric; a later restatement after a reported achievement |

**The failed/revised boundary is not the system's error alone.** Both sides agree in all 8 rows that the
target was not met; they differ on the label. The round-3 guide carries two rules that collide for an
annual target that was missed and then set again: "renewal is not revision" (from round 1) and "missed
and moved: choose revised" (added for this round, §8.2). The system follows the first, the annotator
followed the second in six rows ("re-dated to FY2025 … revision rather than routine annual renewal"),
and round 1 had only the first. The guide line was ours and was ambiguous. Re-deriving the outcome with
the second rule (post hoc, from the stored labels) moves raw accuracy from 0.667 to 0.700 only: it
fixes three rows and breaks one, because the annotator also left some missed annual targets `failed`.
The split between `failed` and `revised` should not be reported from these labels; "not met" should.

**Fields.** 49 of 60 right (0.82; round 1: 0.90). This round the annotator judged the extracted fields
against what the later evidence shows the commitment to be, a stricter test: 8 of the 11 notes say the
extraction lacks a scope or a baseline, and 5 of those that only the later evidence supplies it; the
other 3 are misreadings ("up to 20 %" as 20 %; "explore setting targets" as setting them; a qualifying
age dropped).

Limits: one annotator with an AI-drafted first pass, as before; 4 to 15 rows per stratum; the two
rounds differ in evidence, judge and guide, so the comparison of their rates is between two systems as
wholes; the 299 are the promises left after round 1 took a sample that favoured rare outcomes, so they
are not a random subset of the 374.

## 9. Reporting convention: failed and revised are one class, "not met" (decided 2026-10-04)

Following §8.6, outcomes are reported on four classes: **achieved, not met, unclear, disappeared**. Not
met means the deadline passed without the target being reached, whether the report says it was missed
(`failed`) or gives it a later date or a weaker level (`revised`). The five-way label stays in the data
as detail, e.g. for picking moved-goalpost cases, and is not used for counts, shares or agreement.

What changed with the decision:

- `outcome.reported()` maps the label; `promise-outcomes` prints `reported_outcome` next to the
  five-way counts; `promise-score` returns a `reported` block (accuracy, κ, per class, confusion) and
  its weighted `accuracy` is on the reported classes (`accuracy_five_way` keeps the old one).
- The annotator's guide has one rule where two collided: `failed` and `revised` count the same, with a
  line on when to use which, and an annual target set again for the next year is `unclear` only when no
  result for its own year is reported.
- The judge's rule (`outcome.decide`) is unchanged: on the reported classes the order of its second and
  third steps no longer matters.

The figures of §6 to §8 on the reported classes (weighted to each sheet's pool, 95 % intervals):

| | round 1: v1, first evidence | round 3: v2, trajectory evidence, held out |
|---|---|---|
| accuracy | 0.82 (0.72 – 0.90) | 0.83 (0.71 – 0.93) |
| raw accuracy, κ on the sheet | 0.703, 0.61 | 0.800, 0.71 |
| not met: precision, recall on the sheet | 14/31, 14/14 | 21/27, 21/22 |
| system's own counts over the 374 | achieved 153, not met 62, unclear 134, disappeared 25 | achieved 173, not met 56, unclear 135, disappeared 10 |
| human-verified shares | achieved 36 %, not met 8 %, unclear 49 %, disappeared 5 % | achieved 50 %, not met 13 %, unclear 31 %, disappeared 6 % |
