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

## 2026-10-31 · The agentic arm, on dev

- `src/agentic-rag` rebuilt as a bounded planner over `gw_common.corpus.load("statements")` with a policy per
  question and a fence in code (`agentic.md`). Harness: `company_agentic`, `GW_RETRIEVAL_WORKERS`, an agent block in
  run reports, `--compare --pairs`. It does not read the graph, by decision.
- RQ2 first, because it looked like the case for an agent. Audit of `20261031T053204Z-baseline-rag-rq2` (vote 0.805,
  24 errors): a phrase of the answer was already shown in 14 of the 17 errors checkable by regular expression. Ceiling
  test `20261031T053208Z` (k = 40): shown 16 of 17, vote 0.772, +3 / −7, p = 0.34. Below the stopping line set
  beforehand (fewer than 10 errors from retrieval), so the RQ2 planner prompt was not iterated.
- RQ2 arms: fixed budget `20261031T054118Z` 0.813 (11.6 statements), planner `20261031T054802Z` 0.789 (14.3 statements,
  1.30 calls), p ≥ 0.45 pairwise with hybrid and each other.
- RQ1 `20261031T054130Z`, six arms in one run: `company_agentic` 0.7645, `sentence_only` 0.7686 (+11 / −8, p = 0.65),
  `cross_year_rrf` 0.7988 (+19 / −12, p = 0.28), `local` 0.7745. The gate gave 262 of 331 sentences no evidence. The text
  rule committed in `320a4f1`, before this run started and unchanged since, gave `local` +9 / −0 on its 75 sentences
  (p = 0.004).
  One round of ablations (`20261031T061753Z`, `T061754Z`, `T062526Z`, `T062533Z`) stayed inside the noise.
- Configuration and hypotheses committed in `4a3d35f`. The test attempt stopped when the API account ran out of credit
  (HTTP 429, `credit_balance_exhausted`, chat and embeddings on one key); no metrics written, no test label read.
  Finished runs cost USD 6.20. To resume: `agentic.md`, section 6.
- Judge v3 (`39ffb79`), written after reading the dev errors and notes, on the same statements with a new API key:
  fixed budget `20261031T074640Z` 0.870 (v2 0.813, +9 / −2, p = 0.065), agent `T074637Z` 0.837 (0.789, +9 / −3, p = 0.15), hybrid
  `T074643Z` 0.813 (0.805, +6 / −5, p = 1.00), agent at 500 characters `T074646Z` 0.854. Agent against fixed budget under v3 +2 /
  −6, p = 0.29. Of the 195 statements the planner's actions added, the judge gave a result label to 1. Test still unread;
  v3 is not in the freeze of `4a3d35f`. USD 2.4.
- Two more on dev, then tuning stopped: the agent's evidence keeping only statements the judge's labels used
  (`20261031T081040Z`, simulated verifier) 0.862, fixed budget at five repeats (`20261031T081043Z`) 0.862, against 0.870 at three
  (p = 1.00 for both). USD 1.5.
- RQ2 test split read once (`bfd27d6`, clean; the pipeline, a choice of the project made on those dev numbers, and comparisons T1–T5, Q1–Q3
  committed first). Hybrid v2 `20261031T085152Z` 0.768, v3 `T091251Z` 0.816; fixed budget v2 `T085149Z` 0.764, v3 `T090719Z` 0.808; agent v2
  `T085145Z` 0.784, v3 `T091030Z` 0.840; chosen pipeline `T092745Z` 0.808. Nothing frozen reaches 0.05: T1 +28 / −18, p = 0.18; T3 +5 / −13,
  p = 0.096; T4 p = 0.090; T5 p = 0.065. The filter that looked useful on dev lost. USD 8.5. Cost figures in earlier notes were per judgement;
  per promise at three judgements they are three times the judge's part (`agentic.md`, section 6). RQ1 not run on test.

## 2026-11-03 · Report draft; five timed queries; corpus statistics

- Report draft in the ACL template under `report/` (`main.tex`, `references.bib`, the ACL style files,
  `README.md`), written from `results.md`, `promises.md`, `graph.md`, `baseline.md`, `evaluation.md`,
  the published runs and the agentic system's run on the teammate's branch
  (`results/agent-rag/passage-hybrid` on `dev/luyuanzhi`, 2026-10-20, passage store, label-style
  classifier). Marked pending: every test-split result, the agentic RQ2 arm, the agentic RQ1 arm on the
  statement store with the cited classifier, the retrieval qrels.
- Five example queries (the brief's Question 2) through the corpus tools in every mode (bm25, dense,
  hybrid, hybrid+rerank), k = 5, median of three calls after a warm-up call, statement store
  `d8a62bfe40c6`, one machine: BM25 2–4 ms inside a company filter and 20 ms over the whole store;
  dense and hybrid about 20 ms with the query vector served from the response cache (an uncached query
  adds the embedding round trip); hybrid+rerank 125–572 ms (CPU cross-encoder); the graph's joins on the
  top hit 4–13 ms. Hits and timings in `report/queries/five_queries.{json,md}`.
- Corpus statistics for the report, from the graph's statement table and the chunk stores: 110,314
  statements, 3,401,540 words, 29,309 unique lower-cased word forms, 30.8 words per statement (median
  23, p90 47); the statement store 108,376 chunks / 3,396,185 words, the passage store 18,839 / 4,565,796
  (overlap counted).

## 2026-11-03 · Demo front end over the dev split

- `frontend/` (Streamlit, opt-in dependency group `frontend`): the sidebar switches RQ1 / RQ2 and
  shows the question's definition; the page draws one item of that question's dev split (another at a
  click, or by id), runs it through a chosen registered system under a chosen condition with the steps
  timed live (first-use load, retrieval, the shared classifier or judge once per run, up to three runs
  with a vote), and shows correct / wrong against the gold with the rationale, the citations, every
  evidence span and where it came from, the gold's own context (annotators, agreement, notes), tokens
  and cost, and any cited page rendered from the raw report. A query of one's own can replace the
  sampled item (no gold then). Every run lands in a session log with a CSV download (the course's
  "five queries and their speed"); the published runs under `results/` are listed per task.
- Same rules as the harness: no gold reaches the system, the target sentence is dropped from the
  evidence, shared prompts and default `k`; cached model responses are off by default so timings are
  real. `frontend/core.py` holds the non-UI part, tested in `tests/test_frontend.py` with a fake system.


## 2026-11-04 · The graph line on the RQ2 test split; judge v3 on its dev evidence; merges

- `origin/feat/frontend-demo` merged (`3cfb559`); `origin/dev/agentic-rq2` merged on the branch `merge/agentic-rq2`
  (`ac21acf`, PR #8): the rebuilt agentic arm, judge v3, the agentic batch's published runs and its RQ2 test read of
  2026-10-31. Four doc conflicts resolved by keeping both sides; the agentic branch's `tests/test_agentic.py` taken whole.
- Judge v3 on the trajectory finder's stored dev evidence (`20261104T010004Z-graph-rag-rq2`, published as
  `graph/promise-window-trajectory-v3`, no new retrieval): vote 0.837 against 0.789 under v2, +8 / −2, p = 0.11; κ 0.75,
  macro-F1 0.788; verdict on 5 of 22 gold-unclear both times, settled left unclear 17 → 10 of 101, verdicts right 0.90 both
  times; the 22 human-labelled rows stay at 15 right, the model-labelled rows go 82 → 88 of 101. USD 0.55.
- RQ2 test split read once for the graph line, a frozen system (the finder unchanged since 2026-10-03, judge v2 unchanged):
  `20261104T005955Z-graph-rag-rq2` → `graph/promise-window-trajectory-test`, vote 0.736 (184 of 250), κ 0.57, macro-F1
  0.548, verdict on 11 of 64 gold-unclear, 51 of 186 settled left unclear, verdicts right 131 of 146 (0.90), all 7
  `disappeared` read as unclear, 44 unstable; 11.6 statements, retrieval p50 220 ms, USD 1.00. The hybrid baseline run
  again on the same machine at the same time (`20261104T005711Z-baseline-rag-rq2` → `baseline/promise-window-hybrid-test`):
  0.708 (177), κ 0.53, 18 of 64, 49 of 186, 131 of 155 (0.85), 39 unstable; 20 statements, p50 932 ms, USD 1.24.
  Paired finder against baseline: +20 / −13, p = 0.30.
- The agentic batch's hybrid baseline under v2 scored 0.768 on this split on 2026-10-31 against 0.708 here for the same
  configuration (15 promises, more than the dev run-to-run spread of 0.016). The two batches' manifests record different
  chat-model identifiers: `gpt-5.6-luna` in the 2026-10-31 batch, `gpt-6-luna` in every run made on this machine since
  2026-10-29 (`.env`); the published copies of the 2026-10-29/30 runs under `results/` name `gpt-5.6-luna` while their
  local manifests under `artifacts/runs/` name `gpt-6-luna`. Which identifier the gateway served is to be settled by the
  group; until then test rows are paired within a batch only.
- Judge v3 on the two test evidence files (`--evidence`, no retrieval) started and was stopped by the machine's memory
  pressure after two of three repeats (graph) and one (hybrid); nothing was read from them, the partial directories were
  removed, and both are to be re-run.
- Harness: two runs of one system started in the same second shared one run directory (`<timestamp>-<system>-<task>`),
  which happened when the dev re-judge and the test run were launched together; `new_run_dir` now appends `-2`, `-3`
  on collision (`4999af0d`).
- Report: the agentic method and its RQ1 dev results on the statement store, judge v3, the RQ2 dev table with every arm
  and judge, and the RQ2 test section with the frozen comparisons, the graph line's rows and the pairing within batches.
