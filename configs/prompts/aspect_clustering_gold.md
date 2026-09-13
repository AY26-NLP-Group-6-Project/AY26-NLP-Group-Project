# Aspect clustering gold prompt (v1)

Give this file to the annotating model verbatim. It produces gold clusters for evaluating aspect
canonicalisation; the method being evaluated never sees these labels except through the scorer.

---

You group **sustainability aspect phrases** that name the same thing.

Each input line is one **pool**: up to 12 phrases from the same sustainability category, each with an
example sentence from a Singapore-listed company's report. Partition every pool into groups, so that
two phrases share a group **if and only if they refer to the same aspect at the same level of
detail**. A statement about one phrase would then be evidence about the other.

## Same group

- Spelling, number, word order or determiners differ: "GHG emissions" / "greenhouse gas emissions",
  "anti-corruption policy" / "anti-corruption policies".
- An acronym and its expansion: "OHS management system" / "occupational health and safety
  management system".
- Near-synonyms for the same thing: "water consumption" / "water usage", "staff training" /
  "employee training".

## Different groups

- **Different granularity** — a whole and its part stay apart: "emissions" / "Scope 1 emissions",
  "waste" / "hazardous waste", "safety" / "fire safety".
- **Siblings** stay apart: "Scope 1 emissions" / "Scope 2 emissions", "hazardous waste" /
  "non-hazardous waste", "employee training" / "leadership training".
- **A quantity and a derived measure** stay apart: "energy consumption" / "energy intensity",
  "water usage" / "water efficiency".
- **A thing and an activity or policy about it** stay apart: "biodiversity" / "biodiversity
  conservation programme", "personal data" / "data protection policy".
- **A goal and an instrument** stay apart: "net zero" / "net zero target", "energy efficiency" /
  "energy-efficient lighting".

When unsure, keep the phrases apart. A missed merge costs one cross-year link; a wrong merge joins
two unrelated claims into one timeline.

Use the example sentence only to understand what a phrase means, never to decide by topic similarity
alone: two phrases can appear in similar sentences and still be different aspects.

## Output format

One JSON object per input line, same order, no prose:

```
{"pool_id": "<copied>", "groups": [["<form_id>", "<form_id>"], ["<form_id>"], ...]}
```

- Every `form_id` of the pool appears in exactly one group; singletons are groups of one.
- Copy `form_id` values exactly; do not use the phrase text as the id.
