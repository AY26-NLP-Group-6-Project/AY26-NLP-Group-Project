# Aspect merge verification prompt (v1)

Used by `graph_rag.canonical.verify`. The variable parts are filled per candidate pair; the rules are
the same granularity rules as the gold clustering guideline (`aspect_clustering_gold.md`), written here
as matching rules for the verifier (Peeters et al., "Entity Matching using Large Language Models":
handwritten matching rules and a forced binary answer are standard prompt components; whether
demonstrations help must be tested per model and dataset).

## system

You decide whether two phrases taken from company sustainability reports name the **same
sustainability aspect at the same level of detail**, so that a statement about one would be evidence
about the other.

Answer **Yes** only if all of these hold:
- they differ only in spelling, number, word order, determiners, an acronym versus its expansion, or a
  near-synonym for the same thing ("GHG emissions" / "greenhouse gas emissions", "anti-corruption
  policy" / "anti-corruption policies", "water consumption" / "water usage").

Answer **No** if any of these hold:
- one is broader or narrower than the other ("emissions" / "Scope 1 emissions", "risk management" /
  "risk management process", "GHG Protocol" / "GHG Protocol Corporate Standard");
- they are siblings under a common parent ("Scope 1 emissions" / "Scope 2 emissions", "hazardous waste"
  / "non-hazardous waste");
- one is a quantity and the other a derived measure ("energy consumption" / "energy intensity");
- one is a thing and the other an activity, policy, law or instrument about it ("personal data" /
  "data protection policy", "anti-bribery laws" / "anti-bribery");
- one is a goal and the other an instrument for it ("net zero" / "net zero target").

If unsure, answer No. Reply with exactly one word: Yes or No.

## demonstrations (variant "rules+demos" only)

A: GHG emissions | B: greenhouse gas emissions -> Yes
A: anti-corruption policies | B: Anti-Corruption Policy -> Yes
A: Scope 1 emissions | B: Scope 2 emissions -> No
A: emissions | B: Scope 1 emissions -> No
A: energy consumption | B: energy intensity -> No
A: biodiversity | B: biodiversity conservation programme -> No

## user

Category: {category}
A: {text_a}
   example: {example_a}
B: {text_b}
   example: {example_b}
Same aspect at the same level of detail?
