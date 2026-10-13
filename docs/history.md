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
  50 %, not met 13 %, unclear 31 %, disappeared 6 %. The failed/revised boundary accounted for 8 of 20
  disagreements, partly a guide ambiguity of ours.

## 2026-10-04 · Reporting convention; the prose filter and RQ1

- Decision: outcomes are reported on four classes, achieved / not met / unclear / disappeared
  (`promises.md`). Scorer, run statistics and the annotator's guide follow.
- `results/baseline/all-statements-hybrid-cited`: the sentence-level hybrid over every statement, paired
  against the prose-store run: p = 1.00 (same report), 0.52 (cross year), 0.63 (sentence only). RQ1 does
  not depend on the filter; RQ2 did.

## 2026-10-13 · Documentation reorganised

Notes renamed by topic, published runs grouped under `results/baseline/` and `results/graph/` with
descriptive names, check sheets renamed by what they contain; this file replaces the lettered sections
of the former notes index.
