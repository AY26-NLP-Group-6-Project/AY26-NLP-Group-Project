# The agentic arm

A bounded planner over the shared corpus tools, one retriever for both research questions
(`src/agentic-rag`). The shared classifier and judge read what it returns, unchanged and under the same
budget as every other arm. It reads only the statement store (hash `d8a62bfe40c6`), never the claim graph.

## Frozen before the test split was opened

Configuration, chosen on dev only: RQ1 `AGENTIC_MAX_HOPS=2`, `AGENTIC_SELECT=verified`; RQ2 `AGENTIC_MAX_HOPS=2`.
Prompts: `agentic_rq1_gate.md`, `agentic_rq1_verify.md`, `agentic_rq2_planner.md`.

Dev runs (`gw1000`, `rq2promises`, three repeats) gave these hypotheses, to be read on the test split once:

| # | comparison on test, majority votes, McNemar | what dev showed |
|---|---|---|
| R1 | `company_agentic` against `sentence_only` | +11 / −8, p = 0.65 |
| R2 | `company_agentic` against `cross_year_rrf` | +10 / −14, p = 0.54 |
| R3 | `cross_year_agentic` against `cross_year_rrf` | +12 / −21, p = 0.16 |
| R4 | `local` against `sentence_only`, on the sentences of the frozen text rule (`agentic_rag.analyze`) | +9 / −0, p = 0.004 |
| R5 | the text rule routes to `local`, the rest stay on `sentence_only`, composed from the run's labels | same flips, macro-F1 0.7686 to 0.7924 |
| R6 | the gate routes to the agent's evidence, the rest stay on `sentence_only`, composed | +7 / −2, p = 0.18 |
| Q1 | RQ2 agent, two hops, against the hybrid baseline | +4 / −6, p = 0.75 |
| Q2 | RQ2 fixed budget, no planner (`AGENTIC_MAX_HOPS=0`), against the hybrid baseline | +7 / −6, p = 1.00 |
| Q3 | RQ2 agent, two hops, against the fixed budget | +2 / −5, p = 0.45 |

R4 and R5 were found on dev, from a rule frozen before any full run, so test is their confirmation. Six RQ1
comparisons and three RQ2 ones are made; a p-value near 0.05 is read against that number. Nothing is tuned after
the test split is opened; a configuration that loses is reported as losing.
