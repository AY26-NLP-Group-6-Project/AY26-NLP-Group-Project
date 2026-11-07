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

The third sheet, for two annotators, is `promise-check-pair.xlsx`: 150 promises, the 60 held-out rows
(the earlier labels prefilled as Annotator 1, so those rows gain a second, independent opinion) plus 90
drawn at random from the 239 promises never checked. The group returned it with 137 rows labelled by
both annotators and settled in `final` (13 rows left empty); the two agreed on 123 of 137 (0.898,
κ 0.84). Labels on this sheet: achieved / failed / unclear / disappeared (section 7). Those 137 rows are
the human part of the gold set (section 8) and the reference the model annotators were calibrated on.

## 4. Evidence

### First version, and why it missed the answers

Six statements from the reports of the deadline year and the year after: BM25 over every statement,
dense over the statements that had a vector at the time (the 71,342 sentence-shaped ones), fused by
reciprocal rank fusion. On the round-1 sheet the
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

Result sentences were mostly among the statements without a vector: lines full of figures, or
third-person sentences. A statement that scores in one of the two fused rankings only is put by RRF
(k = 60) below one that is thirtieth in both (1/61 against 2/90). Of the 2,244 statements shown, 37
(1.6 %) came from outside the dense index: the commitments called "unclear" were judged almost without
the sentences that carry results. The knowledge base now carries a vector for every statement
(`baseline.md`), which is what the next version builds on.

### Trajectory evidence (`promises/evidence.py`, mode `trajectory`)

1. **Two complete rankings.** Every statement of a report is ranked by BM25 and by dense similarity
   over the shared statement store (statements under five words are embedded on demand, cached).
2. **A budget per report year**, from the report after the promise up to the year after the deadline:
   6 statements from the first report at or after the deadline, 3 from the next, 2 from each earlier one.
3. **Neighbours.** The statements before and after the two best hits of the deadline report, whatever
   their length: a target table is parsed into one statement per cell, and the result sits beside the
   target.
4. **Linked targets.** Targets the extractor attached as `related` and first stated inside the window,
   at most 3: the promise graph's own join.
5. **Order and adjacency.** Statements are shown in report order; one that follows the previous one in
   the report is marked "directly follows E3", so a target cell and its result are read together.

11.6 statements per promise (max 19), from 2.0 report years; 42 % of them statements the first
version's dense index did not cover.
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

### Any system's retriever (`promise_window`)

The finder above is the graph system's way of answering one question: which statements of the later
reports should the judge read for this commitment. Any registered system answers the same question
through the RQ1 protocol: `promise-evidence --system <name>` turns each checkable promise into a
`Query` under the `promise_window` condition (company, `year_from` = the promise's year + 1, `year_to` =
the deadline + 1, the metric as `aspect`, the record under `meta["promise"]`), calls the system's
`retrieve(query, k=20)` and writes `evidence.<name>.jsonl` in the same shape as the finder's, report
order, E-tags and `follows` derived from the statement ids. The judge then runs on it unchanged
(`promise-outcomes --evidence-from …`, output `outcomes.v2.<name>.jsonl`), and `promise-gold-score`
compares the result with the gold. The graph system serves the condition with the trajectory finder;
the hybrid baseline with its ordinary ranking inside the window; an agentic system with whatever it
plans over the corpus tools (`gw_common.corpus`). The cap of 20 statements is a ceiling, not a target:
the finder's own budgets stay under it (11.6 on average), the baseline fills it.

The same loop runs as an evaluation task: `gw-eval --task rq2 --system <name> --split dev --repeats 3`
takes the gold split, retrieves once per promise, judges `repeats` times, scores the vote against the
gold (accuracy, κ, macro-F1 over the four outcomes, the three rates of section 6, a bootstrap interval)
and writes a run dir that `--publish` and `--compare` read like an RQ1 run (`evaluation.md`, section 4).
The pipeline stages above (`promise-evidence --system`, `promise-outcomes --evidence-from`,
`promise-gold-score`) remain for judging all 374 or re-judging a stored evidence file.

First result (2026-10-30, `gw-eval --task rq2`, dev split of the gold, 123 promises, judge v2 × 3 on each
system's evidence; `results/graph/promise-window-trajectory`, `results/baseline/promise-window-hybrid`):
the finder's evidence and the hybrid baseline's both put the vote at 97 of 123 right (0.789; κ 0.69 and
0.68), paired +4 / −4, McNemar p = 1.00. The baseline is more cautious (a verdict on 3 of the 22
gold-unclear promises against 5, 21 of 101 settled ones left unclear against 17, 94 % of its verdicts
right against 90 %) and less steady (20 promises change label across repeats against 10). Judged over
all 374 through the pipeline (`promise-outcomes --evidence-from`), the baseline's evidence gives
achieved 172, failed 62, unclear 125, disappeared 15 (USD 1.9). As on RQ1, structured and plain hybrid
retrieval are not distinguishable on this split; what the finder adds is the shorter, ordered reading
(11.7 statements against 20) and the lower cost per judgement.

On the test split, read once on 2026-11-04 for this frozen system (`graph/promise-window-trajectory-test`,
`baseline/promise-window-hybrid-test`; `results.md`): the finder 0.736 against the baseline 0.708, +20 / −13,
p = 0.30; verdicts right 0.90 against 0.85, settled promises left unclear 27 % and 26 %. Judge v3 (section 5)
on the same stored evidence: dev 0.789 → 0.837 (+8 / −2, p = 0.11, `graph/promise-window-trajectory-v3`); test
0.736 → 0.804 (+26 / −9, p = 0.006, `graph/promise-window-trajectory-test-v3`) against the baseline's 0.708 → 0.748
(`baseline/promise-window-hybrid-test-v3`), the finder ahead under v3 by +24 / −10, p = 0.024. The agentic system's fixed budget and two-hop planner, run in the same batch on 2026-11-05: 0.748 / 0.744
under v2 and 0.768 / 0.800 under v3; the finder and the agent tie under v3 (+14 / −15, p = 1.00) and the finder
does it with no planner, 11.6 statements against 16.5 and a retrieval p50 of 0.2 s against 11.5 s (`results.md`).

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
judge is not deterministic: about 16 % of promises (58 of 374) do not get the same outcome three
times, almost always a verdict against `unclear`. Cost: USD 1.5 for three runs over the 374 promises
on trajectory evidence.

### Version 3, on dev only

A later judge keeps this design and adds labels for a differently worded measure of the same commitment, a stated part
delivery and a figure compared in code; `--judge v3` selects it, v2 stays the default and every number in this file is
v2. The group checked its three added readings against the two filled sheets (section 3) and found it no less
reliable than v2; the sheet scores in section 6 are v2's. Results and limits: `agentic.md`.

## 6. Results of the held-out check

Weighted to each sheet's pool, 95 % bootstrap intervals:

| | round 1: judge v1, first evidence | round 3: judge v2, trajectory evidence, held out |
|---|---|---|
| raw accuracy, κ, five classes | 0.703, 0.63 | 0.683, 0.59 |
| accuracy, reported classes (failed and revised as one) | 0.82 (0.72–0.90) | 0.82 (0.70–0.92) |
| accuracy, five classes | 0.82 (0.72–0.90) | 0.80 (0.68–0.90) |
| verdict where the check says unclear | 31 % (20–42) | **14 % (2–33)** |
| unclear where the check has a verdict | 0 % | 15 % (3–29) |
| verdicts that are right | 75 % (63–86) | 85 % (74–94) |

The over-commitment fix holds on rows nothing was tuned on, with a wide interval: 17 human-unclear rows
carry it. Overall accuracy did not move: v1 was right 82 % of the time because it said `unclear` often
and was right when it did; v2 on complete evidence says it less and is right 80–82 % of the time. The
price is real: 15 % of the promises the check settles are left `unclear`. (An earlier judge run with the
previous chat model scored 8 % (3–15) and 0.83 on the same sheet; `history.md`, 2026-10-29.)

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
moved-goalpost cases. On the held-out sheet the merged class is right 18 times in 24 and misses 4 of 22.

System counts over the 374 on trajectory evidence: achieved 169, failed 56, unclear 134, disappeared 15.

## 8. The gold set and its split

Every checkable promise carries a settled outcome: `data/eval/rq2promises.pair_gold.a6f35618dd6e.jsonl`
(373 rows, each with its promise record, so the file alone drives `gw-eval --task rq2`) and
`rq2promises.build_report.json`. The one row settled as `not_a_promise` (P00412, a target
horizon read as a deadline) is an extraction error, not an outcome, and the judge has no such label: it
is listed in the build report and stays out of the gold and the split. Two sources, one sheet format,
one guide:

- **137 promises labelled by the group** on the pair sheet (section 3): two annotators, blind, an
  adjudicated `final`; agreement 0.898, κ 0.84.
- **237 promises labelled by model annotators** run as sub-agents under the sheet's guide, three
  boundary clarifications drawn from the first calibration round, and 21–24 worked examples from the
  group's rows. Annotator 1 is the project's default model (Claude Fable), annotator 2 Claude Opus; each
  reads the same eight cells the humans read and nothing else, blind to the other and to the system.
  They agreed on 221 of 237 (0.932); the 16 disagreements went to a third pass that read both notes
  (12 settled for annotator 1, 4 for annotator 2, none to a third label), among them P00412, settled as
  `not_a_promise` and therefore excluded; 236 model-labelled promises remain.
- **Calibration first**, on human rows the annotators had not seen as examples, each round a fresh
  stratified 40:

| round | annotator 1 vs final | annotator 2 vs final | 1 vs 2 | the two humans on the same rows |
|---|---|---|---|---|
| 1, sheet guide only | 0.875, κ 0.82 | 0.850, κ 0.78 (same model as 1) | 0.975 | 0.875, κ 0.82 |
| 2, guide + boundaries | 0.875, κ 0.81 | 0.875, κ 0.81 (same model as 1) | 1.000 | 0.950, κ 0.92 |
| 2, annotator 2 = Opus | 0.875, κ 0.81 | **0.925, κ 0.88** | 0.925 | 0.950, κ 0.92 |

Two instances of one model agree almost perfectly, which makes the pair worthless as a check, so the
second annotator was moved to another model family. Where Fable and Opus agree they match the group's
final 35 times in 37 (0.946). Against the human final the model annotators sit where the humans sit
against each other (0.875–0.925, humans 0.90 over the 137 rows). What remains lies on two boundaries
the humans also split on: `unclear` against `disappeared` when the evidence touches the subject but not
the target, and whether a practice shown running is `achieved`. One known inconsistency: P00136 and
P00141 (Far East's refrigerant roadmap, FY2021 and FY2022) are `unclear` by the model pair, while the
group settled the FY2023 sibling P00144 as `disappeared` on near-identical evidence.

Distribution over the 373: achieved 206, failed 68, unclear 86, disappeared 13.

**Split: dev 123 / test 250**, as for RQ1: about a third dev, stratified by outcome × label source, the
75 promises the judge prompt was tuned on (the round-1 sheet) pinned to dev.

| | dev | test |
|---|---|---|
| achieved / failed / unclear / disappeared | 61 / 34 / 22 / 6 | 145 / 34 / 64 / 7 |
| labelled by the group / by the model pair | 22 / 101 | 115 / 135 |

Tune on dev; test is opened once, for the report, and has been, for the arms in `agentic.md` section 6. On dev the judge of section 5
agrees with the gold on 96 of 123 (0.780, κ 0.67): precision / recall achieved 0.94 / 0.84, failed
0.88 / 0.65, unclear 0.49 / 0.77, disappeared 0.67 / 1.00; it gives a verdict on 5 of the 22
gold-unclear promises (23 %), leaves 18 of the 101 settled ones unclear (18 %), and 90 % of its
verdicts are right.

Files: `kb/annotation/rq2-gold/<round>/` holds, per round, the brief, the reference examples, the
batches as the annotators saw them, their label files (`NN.a1.jsonl`, `NN.a2.jsonl`), `score.json` for
the calibration rounds and `main/adjudication/` for the third pass. `gw-graph promise-gold` rebuilds the
snapshot from these files and the group's sheet; `gw-graph promise-gold-score --gold-split dev` scores a
judge output against it.

## 9. Known limits

- Two human annotators for 137 promises, calibrated model annotators for the other 237; 4 to 15 rows per
  stratum on the earlier check sheets, so their class-level rates carry wide intervals.
- Flattened multi-column tables read across columns (next year's target taken for a result → a wrong
  `achieved`); a bare "this target" from another page mis-attributed. Two prompt clarifications did not
  remove these.
- Scope the text does not settle ("EMG Taiping" against "EMG Plant 2").
- Annual targets renewed at a weaker level are read as renewal.
- Extraction lacks scope or baseline left to context; table-only targets are missing from the pool.
- `unclear` and `disappeared` remain upper bounds on what the reports leave open.

## 10. Reproducing

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
uv run gw-graph promise-gold --sheet kb/annotation/spotchecks/promise-check-pair.xlsx \
    --held-out kb/annotation/spotchecks/promise-check-first-evidence.key.json   # the gold file and split
uv run gw-graph promise-gold-score --gold-split dev                             # a judge against the gold
uv run gw-graph promise-evidence --system baseline-rag                          # any system's evidence (promise_window)
uv run gw-graph promise-outcomes --judge v2 --repeats 3 \
    --evidence-from artifacts/graph/dev/promises/evidence.baseline-rag.jsonl   # -> outcomes.v2.baseline-rag.jsonl
uv run gw-graph promise-gold-score --gold-split dev \
    --outcomes artifacts/graph/dev/promises/outcomes.v2.baseline-rag.jsonl
uv run gw-eval --task rq2 --system graph-rag --split dev --repeats 3       # the same as an evaluation run
uv run gw-eval --task rq2 --system baseline-rag --split dev --repeats 3
uv run gw-eval --compare artifacts/runs/<graph run> artifacts/runs/<baseline run>
```

`--evidence deadline` with `--evidence-from artifacts/graph/dev/promises/outcomes.jsonl` reproduces the
first evidence; `--judge v1` the first judge. Scoring the round-1 sheet against any judge's output
(`--outcomes <file>`) is only meaningful for judges that saw the first evidence.
