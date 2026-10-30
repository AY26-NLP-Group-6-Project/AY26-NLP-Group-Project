# History

The dated record of the graph line, oldest first. Numbers are as first measured; where a later entry
supersedes one, it says so. Run folders refer to `results/`; local run ids are in their manifests.

## 2026-09-10 · Corpus

240 sustainability reports from 56 SGX issuers, 2020–2025, collected from the companies' own IR sites
(11 from SGXNet during the pilot); 10,635 pages, 3.48 M words. Filtering rules and manual verification in
`kb/README.md`. The PDFs are never redistributed.

## 2026-09-12 · Scaffold, first graph build, aspect extraction

- uv workspace, shared schemas and Protocols, frozen datasets, the evaluation runner; `majority` and
  `random` systems give macro-F1 0.226 and 0.311 on the pre-labelled set.
- Graph over the evaluation companies: 233 reports, 108,948 statements, 734 aspects, 19,586 mentions,
  7,146 cross-year edges. All 1,000 evaluation sentences matched a parsed statement. Page furniture
  nearly poisoned the chains (3,682 chains before a sentence filter dropped 23,097 candidate mentions,
  2,804 after); 27 % of cross-year edges join verbatim repeats.
- Aspect extraction by GPT-6 via Codex over 9,320 statements: gate passed, partial F1 0.649, category
  accuracy 0.873, no-aspect false-positive rate 0.264 (`graph.md`). The graph grew to 29,637 mentions
  and 7,503 aspect nodes, 79 % of the new ones singletons.

## 2026-09-13 · Canonicalisation, proof of concept

- Our climate-risk category convention did not match A3CG's; 56 pairs re-mapped, extractor category
  accuracy 0.903 against the re-mapped gold.
- Canonicalisation. Macro and micro metrics rewarded merging nothing on singleton-heavy gold, so the
  gate became pairwise precision ≥ 0.80. HAC at 0.82: wrong merges are parents with children and
  siblings. LLM verification of HAC candidates (top 5, cosine ≥ 0.70, rules with demonstrations chosen
  on validation): on the reused test pools P 0.733 / R 0.750; on a clean test set (81 pools, 811
  phrases, 123 pairs) **P 0.597 [0.49–0.70], R 0.748, F1 0.664** against HAC's 0.467 / 0.463 / 0.465.
  Gate failed; morph normalisation kept. A blind spot-check of the gold (66 pairs) was exported and not
  filled.
- Proof of concept of the graph arms on the first 300 items with pre-labels: no arm below sentence-only
  beyond noise, no measurable gain either; the same prompt re-sampled disagrees with itself on 28 of
  300 labels, so every comparison from here on uses at least three uncached repeats.

## 2026-09-14 · Literature screen on promises and stock prices

Supervisor feedback asked for fulfilled / unfulfilled promises as case studies and suggested a
stock-price correlation. The screen (`market-screen.md`) found the prior effect small or null and the
checkable sample far below the power needed; case studies and fulfilment statistics went ahead, the
market analysis did not.

## 2026-09-19 · Calibration on A3CG

- The shared zero-shot classifier on A3CG's own test splits (gold aspect given): macro-F1 0.748 on the
  full test, 0.714 / 0.723 averaged over seen / unseen folds; the weak class is `indeterminate`, erring
  towards `implemented`; `none` recall 0.56–0.68.
- 93 A3CG statements occur verbatim in our corpus; on those 165 rows, three repeats per condition, no
  evidence arm hurts and none helps significantly (fused +0.018 mean, sign-test p about 0.35).

## 2026-09-29 · Human gold; ordinary RAG against the graph arms

- Annotation finished: 1,000 rows, six annotators, Fleiss κ 0.809 on the 50-row pilot; the three LLM
  pre-annotators agree with the human majority 0.79–0.80. 34 no-aspect rows got an action label and had
  their spans filled by review. Split dev 331 / test 669.
- First run on human gold with the graph arms (evidence cap 300 characters): fused +0.052 over
  sentence-only, p = 0.001, the gain in `indeterminate` (0.559 → 0.683). Superseded the same day: the cap
  was raised to 800 and the baseline added.
- `results/baseline/passage-hybrid` against `results/graph/graph-arms`: passage-level hybrid retrieval
  lands at or below its own sentence-only and no-aspect detection collapses (F1 0.788 → 0.598); graph
  fused is the best arm (vote 0.7810, p = 0.002 against the passage cross-year arm). Two independent
  sentence-only runs differ by 0.025, so only paired tests are quoted across systems. Confound noted:
  the winning arm differed in both graph traversal and sentence-sized evidence.

## 2026-09-30 · Retrieval unit, de-identification, cited classifier, RAG metrics

- `results/baseline/sentence-hybrid`: the hybrid retriever over the sentence store equals graph fused
  (p = 1.000 same report, 0.345 cross year); the retrieval unit was the ingredient, not the graph.
- The annotators' workbook replaced by the de-identified `kb/annotation/eval.xlsx`; the snapshot hash
  changed from `23dc51f1d9de` to `3e18cc14e648` with identical items, labels and split; the two are
  recorded as equivalent.
- `results/baseline/sentence-hybrid-cited`: the classifier now returns a rationale and citations. Asking
  for them costs no accuracy (sentence-only vote 0.7647 against 0.7416 / 0.7591 / 0.7343 before, paired
  p 0.60 / 1.00 / 0.27). Evidence arms within ±0.01 of sentence-only; evidence cited in 7.4 % and 2.0 %
  of items; about 145 more input tokens per item.
- RAG-style metrics on that run: faithfulness 0.94–0.95 flat across conditions, answer relevance 0.62
  everywhere, context relevance 0.46 same report / 0.38 other years, LLM-judged.

## 2026-10-01 · Calibration of the RAG judge

One teammate filled the blind sheet (186 rows): faithfulness agreement 0.976 (the judge stricter than
the person, never lenient); passage relevance agreement 0.831, the judge lenient by about 1.7×, so
corrected context relevance about 0.27 / 0.22. Decision: keep the judge prompt, quote the scores with
the calibration.

## 2026-10-02 · Graph arms under the cited classifier

`results/graph/graph-arms-cited`: graph fused vote 0.7799 against the baseline's cross-year 0.7804, p =
1.00 best against best; graph fused against its own sentence-only +0.020, p = 0.078. Graph lookups 9–11
ms against 117–326 ms for the hybrid path. The graph's case moves to RQ2.

## 2026-10-03 · RQ2: targets, promises, outcomes, two human checks, case studies

- 3,164 candidate statements → 1,273 validated targets (Claude sub-agents, 12 shards; the in-repo small
  model gets 1,462 on the same candidates, statement-level κ 0.79) → 880 promises → 374 checkable.
- First outcome judge (the model names the outcome) over six statements from the deadline-year reports:
  achieved 153, unclear 134, failed 33, revised 29, disappeared 25. Human check of 75 promises
  (`promise-check-first-evidence.xlsx`; one annotator, Codex-drafted first pass): extraction precision
  0.987, fields right 0.905, raw agreement 0.703; the system gave a verdict on 21 of 35 promises the
  check called unclear. Weighted to the 374: achieved 36 %, unclear 49 %, failed 5 %, revised 3 %,
  disappeared 5 %.
- Case studies: ten commitments from eight companies read against every statement of the company
  (`case-studies.md`). The full reading changed 5 of the 10 readings, and 5 of the 11 `disappeared`
  rows were in the reports after all.
- Judge v2: the model labels each statement, a rule names the outcome. On the same 74 rows (used for
  tuning, three prompt versions): raw agreement 0.878, verdicts where the check says unclear 4 of 35.
- Trajectory evidence: the dense ranking had only covered the prose store, so result sentences were
  almost never shown (1.6 % of evidence from outside the store); four hand-found answer statements ranked
  first to third on BM25 and were still cut. New evidence over every later report with both rankings
  complete, a budget per year and neighbours: 6 of 8 hand-found answers shown, 99 promises gain a verdict.
- Held-out check of the final system: 60 promises (`promise-check-trajectory.xlsx`), all judged the same
  day. Weighted to the 299 pool: accuracy 0.80 five-way / 0.83 with failed and revised as one, verdict
  where the check says unclear 8 % (3–15), verdicts right 84 % (71–93). Human-verified shares: achieved
  50 %, failed 13 %, unclear 31 %, disappeared 6 %. The failed/revised boundary accounted for 8 of 20
  disagreements, partly a guide ambiguity of ours.

## 2026-10-04 · Reporting convention; the prose filter and RQ1

- Decision: outcomes are reported on four classes, achieved / not met / unclear / disappeared
  (`promises.md`). Scorer, run statistics and the annotator's guide follow. Renamed on 2026-10-21:
  the class is called failed, and `revised` is no longer a label on the sheets.
- `results/baseline/all-statements-hybrid-cited`: the sentence-level hybrid over every statement, paired
  against the prose-store run: p = 1.00 (same report), 0.52 (cross year), 0.63 (sentence only). RQ1 does
  not depend on the filter; RQ2 did.

## 2026-10-21 · Two-annotator sheet

Teammates can annotate. Decided: the labels are achieved / failed / unclear / disappeared, with a
re-dated commitment counted as failed (the deadline passed without the target being reported as met),
so `revised` leaves the sheets; the judge keeps it internally and reports it as failed. New workbook
`kb/annotation/spotchecks/promise-check-pair.xlsx`: 150 promises, the 60 held-out rows (the user's
earlier labels prefilled as Annotator 1) plus 90 drawn at random from the 239 never checked; columns
for Annotator 1, Annotator 2, adjudication and a final label; a second tab with the guide and live
agreement formulas. `promise-pair-copy` gives a teammate a copy without the first annotator's columns,
`promise-pair-merge` folds it back, `promise-pair-score` reports agreement, the system against each
annotator and against the final label, and the two pools (the 60 weighted by their strata, the 90 as a
plain random sample of the 239).

## 2026-10-13 · Documentation reorganised

Notes renamed by topic, published runs grouped under `results/baseline/` and `results/graph/` with
descriptive names, check sheets renamed by what they contain; this file replaces the lettered sections
of the former notes index.

## 2026-10-29 · One knowledge base, every statement; RQ1 re-run; chat model changed

- Decision: every arm retrieves over every statement of five words or more (108,376, hash
  `d8a62bfe40c6`, store `statements`). The sentence-shape filter is gone from the baseline chunker and
  from the graph's candidate lists; it remains only as the gate before the aspect extractor, since the
  graph's aspects were extracted and human-checked with it. The passage store (`passages`, 18,839,
  `c80d0ab23191`) stays as the granularity ablation; the prose-sentence store (71,342, `b1c181dcaf1a`)
  is retired. Run manifests now record the store the retriever read.
- Chat model: `.env` moved to `gpt-5.6-luna` before these runs; everything below is on it, and the user
  decided to keep it for the whole project from here on. The runs of 2026-09-29 to 10-04 (`gpt-5.6-luna`,
  prose-sentence store) are removed from `results/`; they remain in git at `7731d73`.
- RQ1, cited classifier, 331 dev items, 3 repeats, run ids `20261029T143225Z` (statements),
  `20261029T143232Z` (graph), `20261029T143243Z` (passages):
  - sentence only in the three runs: vote 0.7397 / 0.7498 / 0.7580 (p = 1.00 and 0.77 paired), the
    run-to-run spread again;
  - hybrid over statements: same report 0.7442, other years **0.7767** (+0.037 on its own sentence
    only, p = 0.21); graph other years 0.7449, graph + BM25 fused 0.7668 (+0.017, p = 1.00);
    best hybrid against best graph: +6 / −11 items, p = 0.33;
  - passages against statements, paired: other years 0.7396 against 0.7767, +18 / −7, p = 0.043;
    same report 0.7499 against 0.7442, p = 1.00; the none F1 of passage evidence 0.70 against 0.74;
  - the classifier cites a retrieved span in 1–9 % of items; graph lookups 9 ms (fused 20 ms) p50
    against 191–734 ms for the hybrid path, measured with three runs sharing one machine;
    USD 0.21–0.30 per 1,000 items.
- RQ2: the rule-based judge re-run on the trajectory evidence with the new model (three repeats,
  USD 1.5): achieved 169, failed 56, unclear 134, disappeared 15; 58 of 374 unstable across the three
  runs. Held-out check re-scored against it: accuracy 0.82 (0.70–0.92) on the reported classes, verdict
  where the check says unclear 14 % (2–33) against 8 % (3–15) for the previous model's run, unclear
  where the check has a verdict 15 % (3–29), verdicts right 85 % (74–94). The previous judge output is
  kept locally as `outcomes.v2.trajectory.gpt-5.6-luna.jsonl`; the pair sheet's key still carries the
  previous system labels, so `promise-pair-score` is run with `--outcomes` pointing at the new file.

## 2026-10-30 · RQ2 gold set: the group's sheet plus calibrated model annotators; dev/test split

- The group returned the pair sheet with 137 of 150 promises labelled by two annotators and settled:
  agreement 0.898, κ 0.84 (achieved 70, unclear 32, failed 28, disappeared 7). It replaces the master
  at `kb/annotation/spotchecks/promise-check-pair.xlsx`; the blind copy is gone.
- The other 237 checkable promises were labelled by model annotators run as sub-agents under the
  sheet's guide, blind to each other and to the system, reading exactly the sheet's cells
  (`promises/gold.py`, rounds under `kb/annotation/rq2-gold/`). Calibration on fresh stratified slices of
  40 human rows: round 1 (guide only) 0.875 / 0.850 against the human final, the two humans 0.875 on
  the same rows; round 2 (guide plus three boundary clarifications) 0.875, humans 0.950. Two instances
  of one model agreed 79 times in 80, so annotator 2 became Claude Opus: 0.925 (κ 0.88) on the round-2
  slice, pair agreement 0.925, agreed labels right 35 of 37.
- Main round, Fable + Opus on 237 promises in 16 batches: pair agreement 221 of 237 (0.932); the 16
  disagreements adjudicated by a third pass (12 to annotator 1, 4 to annotator 2). Gold over the 374:
  achieved 206, failed 68, unclear 86, disappeared 13, not a promise 1.
- Split as for RQ1: dev 124 / test 250, stratified by outcome × label source, the 75 round-1 promises
  pinned to dev; dev holds 22 human-labelled rows, test 115
  (`data/eval/rq2promises.pair_gold.14b499a7a5b3.jsonl`, `rq2promises.build_report.json`).
- The judge (v2, trajectory evidence, outcomes of 2026-10-29) against the gold on dev: 0.774, κ 0.66;
  over-commitment 6 of 23, under-commitment 18 of 101, verdict precision 0.89. Test not opened.
- Known soft spot: `unclear` against `disappeared` when the evidence touches the subject but not the
  target; P00136 / P00141 (model pair, unclear) against the group's P00144 (disappeared).
- Revised the same day: the one row settled as `not_a_promise` (P00412) is an extraction error, not an
  outcome, and leaves the gold: 373 rows, dev 123 / test 250, snapshot `f41388d7eb85`, then
  `a6f35618dd6e` once every row carried its promise record (same rows, same split) so the file alone
  drives the evaluation task; the judge on dev 0.780, κ 0.67, over-commitment 5 of 22, under-commitment
  18 of 101, verdict precision 0.90.
- RQ2 became a `gw-eval` task (`--task rq2`, `gw_common/eval/rq2.py`): the system's retriever under
  `promise_window`, the shared judge (moved to `gw_common/judges/promise.py`, v2 by default) run
  `repeats` times over identical evidence, the vote scored against the gold with accuracy, κ, macro-F1
  over the four outcomes, the three RQ2 rates and a bootstrap interval; the run dir, `--publish`, the
  results index and `--compare` (McNemar on the votes) work as for RQ1.
- First two RQ2 runs through it, dev, three repeats (`20261030T063140Z-graph-rag-rq2`,
  `20261030T063123Z-baseline-rag-rq2`, published as `graph/promise-window-trajectory` and
  `baseline/promise-window-hybrid`): vote accuracy 0.789 for both (κ 0.69 / 0.68, macro-F1 0.769 /
  0.771), mean over repeats 0.791 ± 0.005 against 0.783 ± 0.009; paired +4 / −4, p = 1.00. Finder:
  11.7 statements per promise, verdict on 5 of 22 gold-unclear, 17 of 101 settled left unclear, 90 % of
  verdicts right, 10 unstable, USD 0.48. Hybrid top 20: 3 of 22, 21 of 101, 94 %, 20 unstable, USD 0.60.
- One protocol for both questions. `EvidenceCondition.PROMISE_WINDOW`: a promise becomes a `Query`
  (company, year window, metric, the record in `Query.meta`) and any system's `retrieve(query, k)`
  answers it; `promise-evidence --system <name>` writes `evidence.<name>.jsonl`, the judge runs on it
  unchanged and names its output after it. The graph system serves the condition with the trajectory
  finder, the hybrid baseline with its ranking inside the window. New `gw_common.corpus`: the corpus as
  tools (search in four modes, get, neighbours, page, reports, companies), registered under `gw.corpora`
  (`statements` over the chunk store, `graph` adding aspects, follow-ups and related targets), so an
  agentic retriever plans over the same calls the fixed baseline makes.
- First RQ2 baseline arm: `promise-evidence --system baseline-rag` (hybrid, rrf+rerank, k = 20 inside the
  window, 2.0 report years per promise) judged with v2 × 3 (USD 1.9, 61 unstable): over the 374 achieved
  172, failed 62, unclear 125, disappeared 15. On dev against the gold 96 of 123 right (0.780, κ 0.67),
  the same count as the trajectory finder's evidence; the two differ on 13 promises, 5 right each way,
  McNemar p = 1.00; over-commitment 4 of 22, under-commitment 20 of 101, verdict precision 0.92.
