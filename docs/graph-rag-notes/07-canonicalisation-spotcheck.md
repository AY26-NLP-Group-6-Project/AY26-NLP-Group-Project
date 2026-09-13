# 07 · Canonicalisation spot-check (for a teammate, ~15-20 minutes)

## What and why

The graph merges phrases that name the same sustainability aspect. The labels we use to score those
merges were written by the assistant that also built the method, so we need one person to check
whether those labels are sensible. You label phrase pairs **without seeing** the existing labels; we
then compare.

## The file

`artifacts/graph/dev/spotcheck/canon_spotcheck_pairs.csv` — 66 pairs from 10 randomly chosen pools
(upload to Google Sheets). Columns:

| column | what to do |
|---|---|
| `category`, `phrase_a`, `phrase_b`, `example_a`, `example_b` | read only; examples are one report sentence each, to show what the phrase means |
| `label` | **required**: `same` or `different` |
| `unsure` | optional: `y` if you hesitated |
| `notes` | optional: why, especially for `different` pairs that feel close |

Do not reorder or delete rows, and do not edit `pair_id`.

## The rule

`same` = the two phrases refer to the **same aspect at the same level of detail**, so a statement
about one would be evidence about the other.

- **same**: spelling, number, word order, an acronym vs its expansion, or a near-synonym
  ("GHG emissions" / "greenhouse gas emissions", "reduce our carbon footprint" / "carbon footprint
  reduction").
- **different**: one broader or narrower ("carbon footprint" / "carbon footprint of our products"),
  siblings ("Scope 1 emissions" / "Scope 2 emissions"), a quantity vs a derived measure ("energy
  consumption" / "energy intensity"), a thing vs a policy or activity about it ("human rights" /
  "Human Rights Policy"), a goal vs an instrument ("net zero" / "net zero target").

Full guideline: `configs/prompts/aspect_clustering_gold.md`. If a pair is genuinely a coin flip, pick
your best answer and mark `unsure`: those rows are exactly where the guideline needs sharpening.

## After you are done

Save the sheet back as CSV over the same path (or send it), then:

```bash
uv run gw-graph canon-spotcheck-score --config configs/graph.dev.yaml
```

This reports raw agreement, Cohen's kappa and, most usefully, whether the existing labels are
**stricter** than yours (they call `different` what you call `same`) or looser. That decides whether
the M2 precision gap is the method's fault or the guideline's.
