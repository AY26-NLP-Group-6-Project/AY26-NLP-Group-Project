# Canonicalisation gold hand-off (for an outside annotator)

Read this page and `configs/prompts/aspect_clustering_gold.md`; that is the whole job.

## 1. Context in five lines

- The temporal claim graph joins statements on the **aspect**. Right now two phrases join only if
  they are the same words after normalisation, so 79 % of extracted aspects occur once and never form
  a cross-year link.
- M2 merges phrases that name the same aspect, using embeddings and hierarchical clustering (the
  CESI method, WWW 2018). Its similarity threshold must be tuned on labelled data and reported on
  different labelled data.
- Your job is that labelled data: **partition small pools of phrases into same-aspect groups**.
- Precision matters more than recall here. A wrong merge fuses two unrelated claims into one
  timeline; a missed merge only loses one link. The prompt says "when unsure, keep apart" for this
  reason.
- You are again an independent annotator: you did not design the clustering and you do not see its
  output.

## 2. Files

| file | direction | shape |
|---|---|---|
| `configs/prompts/aspect_clustering_gold.md` | given | the instruction prompt, use verbatim |
| `artifacts/graph/dev/canon_pools.jsonl` | given | `{"pool_id", "split", "category", "forms": [{"form_id", "text", "example"}]}` |
| `<your output>.jsonl` | returned | `{"pool_id", "groups": [[form_id, ...], ...]}`, one line per pool, same order |

Ignore the `split` field; it only tells the scorer which pools tune the threshold (`val`) and which
report the result (`test`). Annotate both the same way.

## 3. How the pools were built

Each pool holds up to 12 phrases from one A3CG category: an anchor phrase, its 5 nearest neighbours
by embedding, its 4 nearest by word overlap, and 2 random phrases from the same category. Pools are
disjoint. Mixing the three sources keeps the gold from being shaped by the embedding model that is
being evaluated, and guarantees that every pool contains both likely merges and likely non-merges.

## 4. Validation on our side

```bash
uv run gw-graph canon-tune --labels your_output.jsonl
```

Rejected outright if any pool's groups do not cover each `form_id` exactly once. Otherwise it reports,
following CESI section 7.2, macro / micro / pairwise precision, recall and F1 for:

- `morph`: normalisation only (every normalised phrase its own cluster), the baseline;
- `hac`: threshold swept on the `val` pools (0.70-0.98), best by mean F1, then reported on `test`.

Gate for M2 (revised after the first run): **pairwise precision >= 0.80** on the test pools, threshold
selected by pairwise F0.5 on the val pools. The first version gated on micro precision and selected on
mean F1; on this gold, where most clusters are singletons, merging nothing maximised both.

## 5. Practical notes

- Record model name, version, prompt file hash, and whether temperature was controllable, as in the
  extraction run.
- One pool per request is fine; pools are small.
- Do not merge across pools, and do not reuse groupings from one pool in another: pools are judged
  independently.

## 6. The run that was made (Claude, 2026-09-13)

Gold written by Claude in-session rather than by Codex, after discussion: the method under test is
OpenAI embeddings + HAC, not the annotator, so the circularity that made the extraction run need an
independent model does not arise here. Controls: labelled from pool text only, before any clustering
had been run on the pools; provenance in `canon_gold_claude_20260913.provenance.json`. Remaining risk:
the annotator designed the pipeline and the guideline. A human spot-check of ~10 test pools is
recommended before any M2 number is quoted.
