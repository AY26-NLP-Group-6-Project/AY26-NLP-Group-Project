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

Generate the input on our side with:

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
uv run gw-graph derive
uv run gw-graph stats        # cross-year chains, the M1/M2 gate
```

Extracted aspects are stored with `method='llm'` and are never mixed with `method='gold_span'`, so
every experiment can be re-run with or without them and we can always say which edges came from
where.
