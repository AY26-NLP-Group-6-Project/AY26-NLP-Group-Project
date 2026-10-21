# Dated commitments and what became of them (RQ2)

Following a commitment across a company's reports is a join on (company, target, year), not a
similarity search: this is where the graph line's case was expected to rest once retrieval turned out
not to move sentence classification (`results.md`). It is also what the supervisor asked to see:
fulfilled and unfulfilled promises, with evidence. This file describes the pipeline as it stands and
what the two human checks found; the dated record is in `history.md`, the page-cited cases in
`case-studies.md`.

## 1. Pipeline

| step | what | how | command |
|---|---|---|---|
| candidates | statements that name a year not before their report year and contain a commitment cue | rule, recall-oriented | inside the next step |
| targets | target span, metric, quantity, unit, baseline year, deadline year, kind (quantitative / milestone / qualitative), recurring | LLM under `configs/prompts/target_extraction.md`, then mechanical validation: the span must occur verbatim in the statement, the deadline must not precede the report year | `gw-graph targets` (in-repo model) or `gw-graph targets-export` → outside extractor → `gw-graph targets-ingest --source <tag>` |
| promises | restatements of one commitment across years merged; same-metric commitments with another deadline or quantity linked as `related` | rule, deterministic | `gw-graph promises --source <tag>` |
| checkable | stated before its deadline; deadline ≤ 2025 with a report for that year or the next; metric names something | rule | same |
| evidence | statements from the company's later reports (section 4) | hybrid retrieval, per report year | `gw-graph promise-evidence` |
| outcome | achieved / failed / revised / unclear / disappeared inside the judge; reported and annotated as achieved / failed / unclear / disappeared, a re-dated commitment counting as failed | the model labels each statement, a rule decides (section 5); majority of three runs | `gw-graph promise-outcomes --repeats 3` |
| human check | a blind sheet, scored against the system and weighted back to the pool | `gw-graph promise-sheet`, `gw-graph promise-score --sheet …` |

Grounding. A *promise with verifiable timing* is ML-Promise's notion (Seki et al., EMNLP 2025),
narrowed to commitments that name a deadline year. The outcome classes extend Jiang, Kim & Lu (Nature
Climate Change 2025), who code emissions targets as achieved / failed / disappeared, with `revised` and
`unclear`. Categories are A3CG's.

## 2. Extraction

Extraction is knowledge-base construction, done once, so the stronger reader was used for the store and
the in-repo small model kept as the reproducible path and the comparison. The outcome judgement, by
contrast, is system output and stays on the fixed model.

| | `gpt-5.6-luna`, low effort, in repo | Claude sub-agents, 12 shards |
|---|---|---|
| statements with a target | 1,215 | 995 |
| targets passing validation | 1,462 | 1,273 |
| rejected: span not verbatim | 163 | 0 |
| quantitative / milestone / qualitative | 931 / 223 / 308 | 911 / 216 / 146 |
| marked recurring | 132 | 359 |
| cost | about USD 0.83 | about 1.9 M sub-agent tokens |

Statement-level agreement 0.905, Cohen's κ 0.79. The 260 statements only the small model extracts are
mostly what the specification excludes: "target / performance" table rows where the year names the
result column, results that mention a target in passing, regulatory deadlines. Known recall loss: targets
that sit in flattened tables with the year, the metric and the value in non-adjacent cells have no
contiguous span and are not extracted.

From the sub-agent extraction: 1,273 targets → **880 promises** (138 restated in more than one year; 50
companies) → **374 checkable** (32 companies; 198 quantitative, 107 milestone, 69 qualitative; 161
recurring annual targets; deadlines 2021–2025). Not checkable: 299 with a deadline after 2025, 171
stated in or after their deadline year, 35 with no report for the deadline year, 3 with a bare anaphor
as metric.

## 3. The human checks

Each check is a blind sheet: one row per promise with the statement, the extracted fields, the years it
was restated in, related targets, and the evidence the judge saw, tagged E1, E2, … with report year and
page. The system's proposal is not on the sheet; it is kept in a key file beside it. Three judgements:

1. `promise_ok`: a genuine dated commitment by the company, with the deadline as extracted?
2. `fields_ok`: metric, quantity, unit, baseline right?
3. `outcome`, from the evidence shown.

Sampling takes a floor per proposed outcome so rare classes are present, and at most four rows per
company. Because of that stratification the sheet's raw rates describe no population: `promise-score`
weights each stratum by its size in the pool (the strata sizes are kept in the key) and gives 95 %
bootstrap intervals. Provenance to state in the report: one team member judged every row, working
through a first pass drafted with Codex and used as the interface; the notes record the points settled
personally. It counts as one annotator's judgement with an AI-drafted first pass.

Two rounds were filled, on two versions of the system:

| | round 1 (`promise-check-first-evidence.xlsx`) | round 3 (`promise-check-trajectory.xlsx`) |
|---|---|---|
| system | first evidence, judge v1 | trajectory evidence, judge v2 |
| rows / pool | 75 of 374 | 60 of the 299 not on round 1 (the rows the judge was tuned on) |
| genuine commitment / fields right | 0.987 / 0.905 | 1.000 / 0.817, judged against what the evidence shows the commitment to be |

(A round-2 sheet was drawn on judge v2 with the first evidence and withdrawn unfilled when the evidence
changed.)

A third sheet, for two annotators, is in progress: `promise-check-pair.xlsx`, 150 promises, the 60
held-out rows (the earlier labels prefilled as Annotator 1, so those rows gain a second, independent
opinion and a human–human κ on the rows the headline numbers rest on) plus 90 drawn at random from the
239 promises never checked (whose raw rates estimate that pool directly). Each annotator fills their
own two columns, outcome and note, on a blind copy (`promise-pair-copy`, merged back with `promise-pair-merge`);
disagreements are settled in `adjudicate`, the settled label goes to `final`, and a second tab shows
the guide and the agreement as it forms. Labels on this sheet: achieved / failed / unclear /
disappeared (section 7). `promise-pair-score` reports agreement between the annotators, the system
against each and against `final`, and the two pools separately.

## 4. Evidence

### First version, and why it missed the answers

Six statements from the reports of the deadline year and the year after: BM25 over every statement,
dense over the shared prose-sentence store, fused by reciprocal rank fusion. On the round-1 sheet the
annotator could not tell the outcome of 35 of 74 promises; the case studies then found by hand that 5 of
the 11 `disappeared` promises were in the reports after all.

Ranking the hand-found answer statements under that retrieval showed the mechanism:

| promise | answer statement | BM25 rank | dense rank | fused rank, cut at 6 |
|---|---|---|---|---|
| ThaiBev solar rooftops | "installed solar rooftops at two distribution centers" | 1 | no vector | 7 |
| Jumbo complaints | the FY2022 performance table | 1 | no vector | 9 |
| Gallant Venture GHG | "achieved a 15.4% reduction in GHG emissions" | 3 | no vector | 16 |
| Old Chang Kee electricity | "was 61 kwh per square foot (FY2020: 68 …)" | 3 | no vector | 18 |
| Indofood Agri ISPO | "by 2024 has been postponed" | 5 | 11 | 7 |
| Old Chang Kee accidents | "Requires improvement as we recorded two cases" | none | 10 | 19 |
| Tiong Woon ERP | "In FY2022, we began integrating …" | none | 58 | not ranked |
| Indofood Agri pouch | "has been delayed" (2023 report, deadline 2025) | 1 | 1 | outside the window |

The prose store holds 71,342 of 110,314 statements; result sentences mostly fail its filter (a sentence
without one of its listed verbs, or full of figures). A statement outside the store can score in one of
the two fused rankings only, and RRF (k = 60) puts a first place in one list (1/61) below a thirtieth
place in both (2/90). Of the 2,244 statements shown, 37 (1.6 %) came from outside the store: the
commitments called "unclear" were judged almost without the sentences that carry results.

### Trajectory evidence (`promises/evidence.py`, mode `trajectory`)

1. **Two complete rankings.** Every statement of a report is ranked by BM25 and by dense similarity;
   vectors the store lacks are embedded on demand (23,089 statements, once, cached).
2. **A budget per report year**, from the report after the promise up to the year after the deadline:
   6 statements from the first report at or after the deadline, 3 from the next, 2 from each earlier one.
3. **Neighbours.** The statements before and after the two best hits of the deadline report, whatever
   their length: a target table is parsed into one statement per cell, and the result sits beside the
   target.
4. **Linked targets.** Targets the extractor attached as `related` and first stated inside the window,
   at most 3: the promise graph's own join.
5. **Order and adjacency.** Statements are shown in report order; one that follows the previous one in
   the report is marked "directly follows E3", so a target cell and its result are read together.

11.6 statements per promise (max 19), from 2.0 report years; 42 % of them from outside the prose store.
Checks without new labels: 6 of the 8 hand-found answers are now shown (four through the complete
rankings, one through the wider window, one as a neighbour; the Indofood postponement sentence ranks
8th among many ISPO statements, the Tiong Woon sentence is not reachable by similarity); 26 of the 28
round-1 verdict rows keep every statement the annotator cited. Of the statements the final verdicts rest
on, 352 were retrieved, 12 are neighbours, 1 is linked; 312 come from the deadline-year report, 40 from
the year after, 13 from earlier reports.

One inconsistency, measured: store vectors embed a statement with a "Company (year), page N:" header,
on-demand vectors the bare text. Taking every vector from one store built the same way keeps 91.2 % of
the evidence statements and moves the basis of 3 of 229 verdicts; left as is, because the held-out
check was made on this evidence.

## 5. The judge

### Version 1, and its failure

The model named the outcome from the six statements. On the round-1 sheet it was right on 70 % of rows
(κ 0.63), but every disagreement bar one was a verdict where the check said `unclear`: 21 of 35, always
in the stricter direction. Its `failed` and `revised` verdicts held 53 % and 38 % of the time. Causes,
from the notes: a result from a later year read as the deadline year's; a different metric, level or
scope taken for this target ("reduce to 15 %" as "reduce by 15 %"; absolute withdrawal for an intensity
target); an annual target set again for the next year read as a moved deadline; a verdict inferred
rather than stated.

### Version 2: labels per statement, outcome by rule

The model answers three questions per statement and one per promise
(`configs/prompts/promise_outcome_v2.md`):

| label | values | question |
|---|---|---|
| `relation` | this_target / same_metric / other | the very commitment (same metric measured the same way, same scope, same level and baseline); its metric only; something else. In doubt, same_metric |
| `deadline_result` | met / missed / none | does it state the result for the deadline year? Results of other years, progress, partial results, inferences and bare target cells are none |
| `change` | later / none | is it itself a commitment or notice giving this target a later or no date, or saying it was postponed? |
| `annual` (per promise) | true / false | a per-year performance level of the kind set again every year? |

`outcome.decide` then applies a fixed rule; a result or a change only counts on a `this_target`
statement, and the calendar is enforced (a report before the deadline year cannot state a miss or an
annual target's result, though it can report a deliverable finished early or a moved deadline):

1. a `met` and no `missed` → achieved;
2. no `met`, a `later`, promise not annual → revised (a moved goalpost explains a miss; for an annual
   target a later year is routine renewal);
3. no `met`, a `missed` → failed;
4. otherwise any `this_target` or `same_metric` statement from the deadline year on → unclear;
5. otherwise → disappeared.

A reply that does not label every statement is `unclear`. The outcome is the strict majority of three
uncached runs; no majority is `unclear`. Grounding: `unclear` is the "not enough information" class of
claim verification (FEVER), defaulting to it is abstention, and per-statement questions are claim
decomposition (`evidence-ledger.md`).

On the round-1 rows, which the three versions of the prompt were tuned on, judge v2 with the first
evidence scores 0.88–0.92 raw and gives a verdict on 2–4 of the 35 unclear rows; the model's own
outcome in the same reply reaches 0.81, so the rule adds to the questions, mostly on `revised`. The
judge is not deterministic: about 15 % of promises do not get the same outcome three times, almost
always a verdict against `unclear`. Cost: USD 1.5 for three runs over the 374 promises on trajectory
evidence.

## 6. Results of the held-out check

Weighted to each sheet's pool, 95 % bootstrap intervals:

| | round 1: judge v1, first evidence | round 3: judge v2, trajectory evidence, held out |
|---|---|---|
| raw accuracy, κ, five classes | 0.703, 0.63 | 0.667, 0.57 |
| accuracy, reported classes (failed and revised as one) | 0.82 (0.72–0.90) | 0.83 (0.71–0.93) |
| accuracy, five classes | 0.82 (0.72–0.90) | 0.80 (0.68–0.90) |
| verdict where the check says unclear | 31 % (20–42) | **8 % (3–15)** |
| unclear where the check has a verdict | 0 % | 15 % (4–24) |
| verdicts that are right | 75 % (63–86) | 84 % (71–93) |

The over-commitment fix holds on rows nothing was tuned on. Overall accuracy did not move: v1 was right
82 % of the time because it said `unclear` often and was right when it did; v2 on complete evidence says
it less and is right 80–83 % of the time. The price is real: 15 % of the promises the check settles are
left `unclear`.

What the commitments did, human-verified:

| outcome | first evidence (round 1, pool 374) | complete evidence (round 3, pool 299) |
|---|---|---|
| achieved | 36.0 % (27.9–42.1) | **50.1 % (40.7–58.7)** |
| failed, including re-dated | 7.6 % (4.7–10.5) | **12.8 % (7.9–20.5)** |
| unclear | 48.7 % (39.8–57.7) | **30.9 % (21.9–39.0)** |
| disappeared | 5.3 % (3.8–6.7) | 6.2 % (0.7–13.9) |
| not a promise | 2.4 % | 0 % |

Where the outcome can be told, four in five commitments were met (50.1 of 62.9) and one in five was
missed or re-dated. The annotator, shown the complete evidence, could not tell the outcome for 31 % of
commitments, not 49 %: about a third of the earlier `unclear` was the retrieval. The two rounds are
different samples weighted to different pools, and differ in evidence, judge and guide, so the comparison
is between two systems as wholes.

By the outcome the system proposed:

| system says | pool | sampled | check agrees | otherwise |
|---|---|---|---|---|
| achieved | 143 | 14 | 13 | 1 revised |
| unclear | 116 | 15 | 11 | 2 achieved, 2 disappeared |
| revised | 21 | 13 | 8 | 2 unclear, 2 failed, 1 achieved |
| failed | 15 | 14 | 5 | 6 revised, 3 unclear |
| disappeared | 4 | 4 | 3 | 1 unclear |

The 20 disagreements: 8 are failed against revised (both sides agree the target was not met); 6 are a
verdict where the check says unclear (three of them a scope or table column the text does not settle);
4 are unclear where the check has a verdict (two achieved the annotator inferred, two disappeared); 2 are
achieved against revised.

Fields: 49 of 60 right. This round the annotator judged the extracted fields against what the later
evidence shows the commitment to be: 8 of the 11 misses are a scope or baseline the promise sentence
left to its context (5 of them only the later evidence supplies), 3 are misreadings ("up to 20 %" as
20 %; "explore setting targets" as setting them; a qualifying age dropped).

## 7. Reporting convention: a re-dated commitment is a failed deadline

The judge's five labels include `revised`, a commitment given a later date or a weaker level without
the original being reported as met. Whether such a row is `failed` or `revised` turned out to depend on
whether a missed target that is set again counts as re-dated: the round-3 guide carried two rules that
collided there (ours), the annotator followed one in six rows and the other elsewhere, round 1 had only
the first, and the system follows the first. Re-deriving the outcome with the other rule moved raw
accuracy from 0.667 to 0.700 only.

Decision (2026-10-04, renamed 2026-10-21): the deadline was stated; if the deadline year passed without
the target being reported as met, the outcome is **failed**, whether the report admits the miss or
moves the date. Outcomes are reported and, from the two-annotator sheet on, annotated on **achieved /
failed / unclear / disappeared**. `outcome.reported()` maps `revised` to `failed`; `promise-outcomes`
prints the merged counts; `promise-score` returns a `reported` block and its weighted `accuracy` is on
the merged classes (`accuracy_five_way` keeps the judge's own labels apart); the guide has one rule.
The judge's rule is unchanged, and `revised` stays in its output as detail, for example to pick
moved-goalpost cases. On the held-out sheet the merged class is right 21 times in 27 and misses 1 of 22.

System counts over the 374 on trajectory evidence: achieved 173, failed 56, unclear 135, disappeared 10.

## 8. Known limits

- One annotator with an AI-drafted first pass; 4 to 15 rows per stratum, so class-level rates carry wide
  intervals.
- Flattened multi-column tables read across columns (next year's target taken for a result → a wrong
  `achieved`); a bare "this target" from another page mis-attributed. Two prompt clarifications did not
  remove these.
- Scope the text does not settle ("EMG Taiping" against "EMG Plant 2").
- Annual targets renewed at a weaker level are read as renewal.
- Extraction lacks scope or baseline left to context; table-only targets are missing from the pool.
- `unclear` and `disappeared` remain upper bounds on what the reports leave open.

## 9. Reproducing

```bash
uv run gw-graph targets-export                          # shards for an outside extractor
uv run gw-graph targets-ingest --source claude
uv run gw-graph promises --source claude
uv run gw-graph promise-evidence --evidence trajectory
uv run gw-graph promise-outcomes --judge v2 --evidence trajectory --repeats 3
uv run gw-graph promise-sheet --judge v2 --evidence trajectory --limit 60 --seed 20261005 \
    --exclude-sheets kb/annotation/spotchecks/promise-check-first-evidence.xlsx \
    --out kb/annotation/spotchecks/promise-check-trajectory.xlsx
uv run gw-graph promise-score --sheet kb/annotation/spotchecks/promise-check-trajectory.xlsx
```

`--evidence deadline` with `--evidence-from artifacts/graph/dev/promises/outcomes.jsonl` reproduces the
first evidence; `--judge v1` the first judge. Scoring the round-1 sheet against any judge's output
(`--outcomes <file>`) is only meaningful for judges that saw the first evidence.
