# 05 · Aspect extraction hand-off (for the GPT / Codex side)

Read this page and `configs/prompts/aspect_extraction.md`; that is the whole job. Nothing else in
the repo is required.

## 1. Context in five lines

- We are building a **temporal claim graph** over Singapore-listed companies' sustainability
  reports: statements → aspects → the same aspect across years, so a 2022 promise can be checked
  against 2024 evidence.
- 1,000 sentences are already annotated by us with aspect spans and action labels; the other
  ~108,000 parsed statements are not.
- Your job is the missing half: **find the sustainability aspects in those unannotated sentences**.
- The graph joins statements on the aspect, so a missed or invented aspect is a missing or false
  cross-year link. Precision matters as much as recall.
- You are deliberately a different model family from the one that produced our labels, so that
  "which spans are aspects" and "what action does the sentence express" do not share one bias.

## 2. What you do NOT do

- No action labels (implemented / planning / indeterminate). Different task, different scorer.
- No paraphrasing, no cleaning, no spelling fixes: spans are copied characters.
- No new categories: the ten in the prompt are closed.
- No opinion on greenwashing.

## 3. Files

| file | direction | shape |
|---|---|---|
| `configs/prompts/aspect_extraction.md` | given to you | the instruction prompt, use verbatim |
| `artifacts/graph/dev/extract_input.jsonl` | given to you | `{"stmt_id", "text", "company", "year"}` per line |
| `<your output>.jsonl` | you return | `{"stmt_id", "spans": [{"text", "category"}]}` per line, same order |
| `data/eval/extract_gold.jsonl` | given to you **only if you want a dry run** | 1,000 sentences with 1,098 gold spans |

Both files already exist on our side (regenerate with the commands below):
`artifacts/graph/dev/extract_input.jsonl` holds **9,320 statements** (40 sampled per report, junk
pre-filtered), `data/eval/extract_gold.jsonl` holds **1,000 sentences / 1,098 gold spans**.

Regenerate with:

```bash
uv run gw-graph export-extract --per-report 40 --out artifacts/graph/dev/extract_input.jsonl
uv run gw-graph export-gold            # writes data/eval/extract_gold.jsonl
```

## 4. Calibrate yourself before the real run

Run the prompt over `data/eval/extract_gold.jsonl` (ignore its `spans` field, that is the answer
key), then score:

```bash
uv run gw-graph score-extraction --pred your_output.jsonl
```

The scorer prints exact-match and partial-match precision/recall/F1 (greedy one-to-one span
matching, partial = token Jaccard ≥ 0.5), category accuracy on matched spans, how many predicted
spans were not literal substrings, and the false-positive rate on the 197 sentences that genuinely
have no aspect.

## 5. The gate (A8)

Output enters the graph only if all three hold:

| metric | threshold |
|---|---|
| partial-match F1 | ≥ 0.60 |
| category accuracy on matched spans | ≥ 0.70 |
| false-positive rate on no-aspect sentences | ≤ 0.35 |

Reference band, so the numbers mean something: A3CG's fine-tuned T5 scores **76.28** aspect-term-
extraction F1 on the full dataset, **75.75** on seen categories and **46.51** on unseen ones
(A3CG Table 14). Our sentences mix seen and unseen categories, and you are prompted rather than
fine-tuned, so ≥ 0.60 partial F1 is a real but reachable bar. `score-extraction` exits non-zero when
the gate fails.

Two failure modes we care about more than the headline F1:

- **Invented aspects on empty sentences.** Page furniture ("Please refer to pages 81 to 104…"),
  financial commentary and company boilerplate must come back as `[]`.
- **Spans that are not substrings.** These are unusable: the graph cannot anchor them. The scorer
  counts them separately; the target is zero.

## 6. Practical notes

- Batch 20–50 sentences per request; keep `stmt_id` on every line so order can be recovered.
- Temperature 0, and record model name, version and the prompt file hash — we write all three into
  the graph build manifest, and a run we cannot reproduce cannot go in the paper.
- Sentences come from PDF text, so some are fragments or table debris. Fragments get `[]`; do not
  try to reconstruct them.
- British and American spellings both occur ("optimisation" / "optimization"). Category names in
  your output must use the spelling from the prompt table.
- If a sentence is not English, return `[]`.

## 7. What happens to your output

```bash
# after the gate passes
uv run gw-graph aspects --config configs/graph.dev.yaml --extracted your_output.jsonl
uv run gw-graph derive  --config configs/graph.dev.yaml
uv run gw-graph stats                       # cross-year chains
```

Ingestion validates every row and counts what it throws away: unknown `stmt_id`, span that is not a
literal substring of the sentence, category outside the ten, empty span. Rejects are reported, not
silently dropped, so a systematic formatting mistake shows up immediately rather than as a quietly
smaller graph.

Extracted aspects are stored with `method='llm'` and are never mixed with `method='gold_span'`, so
every experiment can be re-run with or without them and we can always say which edges came from
where.

## 8. Run 1 · GPT-6 via Codex, 2026-09-12 — independent review

Artefacts: `artifacts/graph/dev/extraction_gpt6_20260912/` (manifest, prompt copy, per-batch inputs
and predictions, merged outputs, validation and score reports).

### 8.1 What was re-checked on our side, and the result

| check | result |
|---|---|
| SHA-256 of gold, corpus input, both prediction files, prompt copy vs manifest | all match; prompt copy byte-identical to `configs/prompts/aspect_extraction.md` |
| merged predictions vs concatenated batches | same 1,000 / 9,320 records (bytes differ only in formatting) |
| strict validation, re-implemented independently: row count, id order, exact keys, closed category set, case-sensitive verbatim substring, empty or duplicate spans | 0 problems on 1,000 calibration rows (1,387 spans) and 9,320 corpus rows (11,095 spans) |
| repo scorer re-run on calibration | reproduces the reported metrics exactly |
| gate A8 | **passed**: partial F1 0.6487 (>= 0.60), category accuracy 0.8734 (>= 0.70), no-aspect false-positive rate 0.2640 (<= 0.35). Excluding the three gold rows exposed before the run: 0.6473 / 0.8727 / 0.2640, still passes |

### 8.2 What the numbers do not say

- **Measured precision (0.58 partial) is a lower bound.** In an 18-span random sample of predicted
  spans with no gold match, about 11 were defensible aspects our gold had skipped — mostly further
  items in enumerations ("risk assessment" next to gold "hazard identification", "community
  engagement", "Anti-Commercial Bribery and Integrity Agreement") — about 3 were borderline and about
  4 were real errors (a span running across a verb, a listing-rule reference, a reporting framework
  name). This is one reviewer's read of their own gold; a human adjudication sample is needed before
  a corrected precision can be quoted.
- **False positives on no-aspect sentences are mostly real errors.** In a 10-sentence sample, about 6
  were pointer or meta sentences ("Please refer to pages 93 to 117 … corporate governance practices",
  "Information on the governance structure is further provided in section 3.3") where the prompt's
  own worked example says `[]`.
- **Most category disagreements are convention, not error.** On matched spans the top disagreements
  are emissions control -> management (26), business compliance -> management (20) and waste
  management -> resource optimisation (14). Checked against the A3CG release itself
  (`tmp/data/a3cg/full`, 2,004 statements): climate-risk aspects ("climate risk",
  "climate-related risks and opportunities", "climate risk assessment") are **management** 7 times
  and emissions control 0 times, while climate targets/ambition/action are emissions control
  (4). So on climate risk the extractor follows A3CG and our LLM_pre convention does not. Ethics
  and code-of-conduct aspects are split in A3CG (business compliance 26, management 9); packaging
  and waste reduction are waste management 10 of 13, so there the extractor deviates, not us.
- **Span boundaries are not the problem.** On partially matched spans, 636 have the same length as
  gold, 89 are longer and 81 shorter.
- **The corpus batch looks like report text should.** 29.7 % of rows are empty (A3CG: 22 % in its
  splits, 33 % overall), 1.19 spans per row, 5 % single-word spans.

**Follow-up (2026-09-13).** Our gold was re-mapped to the A3CG convention for climate aspects (56
pairs, emissions control -> management for climate risk, disclosures and scenario analysis). Against
the re-mapped gold the same predictions score category accuracy **0.903** (was 0.873); partial F1
0.649 and no-aspect false-positive rate 0.264 are unchanged. The prompt is now **v2** and states the
climate split explicitly; run 1 used v1, whose copy stays in the run folder (`prompt.md`, sha256
`e6783b7b…`), so any re-run must record which version it used.

### 8.3 Criticisms from the run that were accepted and fixed

- The scorer's `exact` metric was token-set equality, not boundary equality, and its substring count
  normalised text. Now reported as `boundary_exact` (characters up to case and whitespace, F1 0.5111),
  `token_set_exact` (F1 0.5119) and `partial`; the substring count is strict and case-sensitive
  (`spans_not_verbatim_substring`, 0 for this run).
- Ingestion now enforces the verbatim contract case-sensitively, matching the prompt.

### 8.4 Reproducibility limits that travel with every result built on this run

- Model recorded as the session identity "GPT-6"; no immutable snapshot id was available.
- Temperature was not controllable and is recorded as `null`, not 0.
- Gold rows `eval0001`-`eval0003` were visible before calibration; both scores are kept.

### 8.5 Effect on the graph

| | before | after |
|---|---|---|
| mentions | 19,586 | 29,637 (+10,051 `llm`; 1,044 duplicates of an existing string match kept the older provenance) |
| aspect nodes | 734 | 7,503 (+6,769 `llm`) |
| statements with >= 1 aspect | — | 20,185 |
| cross-year chains (>= 2 years) | 2,804 | 3,932 (1,251 contain an `llm` mention; 1,095 sit on llm-only aspect nodes) |
| `follows_up` edges | 7,146 | 8,563, of which 28.1 % link verbatim repeats |

**5,334 of the 6,769 new aspect nodes (79 %) occur exactly once.** Exact-match aspect identity
fragments free-text spans: "scope 1 and 2 emissions", "scope 1 and scope 2 ghg emissions" and
"direct emissions" never meet. This makes M2 canonicalisation the binding constraint on the graph,
not extraction. A pre-ingestion copy is kept at `artifacts/graph/dev/graph.pre_llm.duckdb`.
