# Graph-RAG notes · roadmap

Working notes for the Graph-RAG line of Proposal 3 (Greenwash-RAG). Started 2026-09-12.
These are design notes, not a proposal: they fix the interfaces first so that the baseline RAG,
the graph RAG and any later agentic variant are measured by the same harness.

- `01-graph-schema.md` — what the graph contains and how it is built
- `02-repo-and-tooling.md` — uv workspace, layout, commands
- `03-eval-contract.md` — what every system must implement to be evaluated
- `04-api-contract.md` — FastAPI surface for the front end

## 1. Why a graph at all

Hybrid retrieval (BM25 + dense + RRF) ranks passages by similarity. Three things we need are not
similarity problems:

1. **Same company, same aspect, other year.** ESG language is templated, so nearest-neighbour
   search returns other companies' near-identical sentences. The constraint we want is an exact
   join on `(company, canonical_aspect, year)`.
2. **Promise fulfilment.** "Did the 2022 `planning` statement become an `implemented` statement or
   a metric by 2024?" is a two-hop traversal, not a ranking.
3. **Moved goalposts.** Baseline-year changes, restated figures and quietly dropped targets are
   comparisons between structured records.

Prior art: EmeraldMind (WWW 2026) already ships an ESG KG (EmeraldGraph, 53,748 entities /
59,344 relations over 37 reports) with EM-KGRAG ablations, **but it has no temporal dimension**;
ML-Promise is single-year; A3CG never compares across years. So the defensible contribution is a
**temporal claim graph**, not "an ESG knowledge graph".

## 2. Scope and non-goals

In scope:

- A narrow, mostly deterministic property graph over the existing `kb/` corpus
  (240 reports, 56 companies, 2020–2025) — see `01-graph-schema.md`.
- Graph traversal as an *evidence provider* for the existing RQ1 ablation, i.e. one more arm:
  `sentence-only / +local / +same-report (RRF) / +cross-year (RRF) / +cross-year (graph)`.
- Trajectory reconstruction (RQ2) as a graph query.

Non-goals for this pilot:

- Open-domain LLM entity extraction over the whole corpus (error compounds, nothing to validate it against).
- Community summarisation à la Microsoft GraphRAG — our queries are local and structured, not global.
- Free-form ReAct agents. An agentic arm, if any, is a bounded traversal policy (`04` + `03`).

## 3. Labels used in this pilot

The pilot runs against **`LLM_pre`** (the pre-filled labels in `kb/annotation/GW_master_1000.xlsx`),
because human annotation is still in flight. Current signal: on the rows two annotators have
completed, agreement with `LLM_pre` is ~86 %.

Rules we hold ourselves to:

- Every eval artefact records `label_source` (`llm_pre` | `human_majority`) and the dataset build hash.
- `uv run gw-eval --labels human` re-runs everything unchanged once the pilot gold lands.
- No headline number in the report/paper is quoted from `llm_pre` runs; they are development numbers.
- Systems never see `LLM_pre` as input — it is only ever the target.

## 4. Phases and gates

| Phase | Deliverable | Gate to proceed |
|---|---|---|
| **M0 scaffold** ✅ 2026-09-12 | uv workspace, `src/common` (schemas, Protocols, registry, frozen datasets, metrics, runner, report, FastAPI factory), stubs for `baseline-rag` / `graph-rag` / `agentic-graph-rag`, 8 tests | done: `gw-data build gw1000` froze 1,000 items at `fddce492c10d`; `gw-eval --system majority` gives macro-F1 0.2264 / acc 0.5143, `random` 0.3109 / 0.2877; both write `metrics.json`, `manifest.json`, `report.md` |
| **M1 graph build (narrow)** ✅ 2026-09-12 | 52 companies, 233 reports, **108,948 statements**, 734 aspects, 19,586 mentions, 7,146 `follows_up` edges, DuckDB store, 13 tests | **passed**: 2,804 cross-year chains (1,931 span >=3 years) against a gate of 20; all 1,000 eval sentences matched a parsed statement, so the graph joins the eval set exactly |
| **M2 canonicalisation** ❌ gate failed on a clean test set 2026-09-13 | Fresh test set: 81 pools, 811 phrases, 123 gold pairs, disjoint from the tuning pools, labelled before any method ran on it; configurations frozen from val. Pairwise P / R / F1: HAC@0.82 **0.467** [0.37-0.58] / 0.463 / 0.465; LLM-verified merges **0.597** [0.49-0.70] / **0.748** [0.63-0.87] / **0.664**. The earlier 0.733 on the reused test pools was optimistic. Graph keeps morph canonicalisation. Blind human spot-check of the gold exported (66 pairs, 07-canonicalisation-spotcheck.md) | pairwise precision >= 0.80: the 95 % CI now excludes it, so the method fails unless the spot-check shows the gold is stricter than people are |
| **M3 metrics & targets** | regex + unit extraction (Scope 1/2/3, kWh, m³, tCO₂e, %, target year, baseline year) | precision ≥0.9 on a 100-row manual check |
| **M4 retrieval arm** | `graph-rag` implements `Retriever`; RQ1 five-condition ablation runs end to end | graph arm reported next to RRF arm, whatever the sign of the delta |
| **M5 trajectories** | `TrajectoryBuilder`; transition F1 on the ~60 (company, aspect) trajectory set | — |
| **M6 serving** | FastAPI app exposing classify / retrieve / trajectory / subgraph | p95 latency ≤8 s end to end |
| **M7 agentic arm** | bounded traversal policy (plan, rewrite, traverse, stop), ≤3 hops, hard timeout; reported in the same ablation table as the other arms | runs under the same harness with cost and latency reported; a loss is a result, not a reason to hide it |

## 4b. What M1 actually showed

- **The splitter port is exact.** 1,000/1,000 eval sentences matched a parsed statement by normalised
  text inside their own report. The graph and the eval set share identity, which the whole design
  depends on.
- **Page furniture nearly poisoned the chains.** The first run produced 3,682 chains, but spot checks
  found links anchored on GRI content-index rows repeated across years ("Page 25 of 26 GRI Reference
  Disclosure Response 102-54 …"). Adding a sentence filter to the string-match step dropped 23,097
  candidate mentions and left 2,804 chains on real sentences. Numbers that pass a gate still have to
  be read.
- **27 % of cross-year edges link verbatim repeats.** 1,922 of 7,146 `follows_up` edges join two
  identical sentences a year apart — templated reporting, which is a finding rather than a bug. Edges
  now carry `same_text`, so the trajectory task can separate "the claim progressed" from "the
  paragraph was copied".
- **The labelled part of the graph is thin, as expected.** Only 392 chains contain at least one
  action-labelled statement, and just 6 have labels at two different years. That gap is precisely
  what the D3 extractor plus a classifier fill; until then the graph knows *where* an aspect is
  discussed, not *what was claimed*.

## 4c. What the first M2 run showed

- **The metrics we planned to gate on cannot separate methods on this gold.** 87 % of gold clusters
  are singletons, so merging nothing scores micro precision 1.0 and macro/micro F1 0.95/0.94 on the
  test pools, above every clustering. Only the pairwise metrics discriminate (no-merge: pairwise
  recall 0). Threshold selection moved from mean F1 to **pairwise F0.5** and the gate from micro
  precision to **pairwise precision**. This change was made *after* test numbers had been seen, so
  the reported test figures are no longer a clean held-out estimate; a fresh set of test pools is
  needed before any M2 number goes into the report.
- **Embeddings measure topical closeness, not identity at the right granularity.** At 0.82 the wrong
  merges are parents with children ("GHG Protocol" + "Greenhouse Gas Protocol Corporate Standard",
  "risk management" + "risk management process"), siblings (the Corporate Standard + the Scope 3
  Standard) and things with instruments ("anti-bribery and anti-corruption laws" + "anti-bribery and
  corruption"). The missed merges are re-ordered paraphrases ("Policies relating to anti-corruption
  and bribery" / "anti-corruption and bribery policies") and programme-name variants ("Connext ED").
  Lowering the threshold to 0.74 raises recall to 0.61 but drops precision to 0.28 [0.18-0.40].
- **Measured precision depends on how strict the gold is.** The guideline keeps granularity levels
  apart and says "when unsure, keep apart"; some kept-apart pairs (e.g. "anti-corruption related
  policies" / "anti-corruption and bribery policies") many readers would merge. A human spot-check of
  the gold is needed to know how much of the precision gap is the method and how much the guideline.
- **Small test set.** 44 gold same-aspect pairs in the test pools; confidence intervals are wide.

Next step for M2 (to be grounded before building): use HAC at a low threshold only to *propose*
candidate merges and let an LLM verify each candidate under the same granularity rules, the analogue
of the side information CESI adds on top of embeddings.

## 4d. M2b: LLM-verified merges (2026-09-13)

- **Method.** Within each category (here: each pool), every phrase's top-5 embedding neighbours with
  cosine >= 0.70 become candidate pairs (EDC retrieves top-5). `gpt-5.6-luna` answers Yes/No under the
  gold guideline written as matching rules; clusters are unions of accepted pairs that never cross a
  rejected pair. Temperature could not be set for this model (`temperature_applied=False`); every
  response is cached, so re-runs are identical.
- **Candidate recall is not the bottleneck.** 68 of 70 val and 40 of 44 test gold pairs are among the
  candidates.
- **Variant selection on val only.** rules: P 0.778 / R 0.900 / F0.5 0.799; rules+demos: P 0.819 /
  R 0.971 / F0.5 0.846 -> rules+demos. Consistent with Peeters et al., who find demonstrations help
  strong GPT models on most, not all, datasets.
- **Test, run once for this method:** P 0.733 [0.55-0.88], R 0.750, F1 0.742 (M2a at its val-selected
  threshold: 0.472 / 0.386 / 0.425). 317 LLM calls, 157,612 input tokens.
- **What the 27 accepted non-gold pairs are.** About two thirds break the rules the verifier was given:
  broader vs narrower ("electricity and fuel consumption" ~ "fuel and energy consumption", "clean
  and/or renewable energy" ~ "clean energy"), thing vs instrument ("social distancing" ~
  "safe-distancing measures"), class vs instance ("oil spill contingency plan" ~ "SOPEP"), different
  referents ("customer privacy" ~ "data privacy"). About one third are calls the gold itself marked
  as borderline and kept apart under "when unsure, keep apart" ("employment contracts" ~ "Written
  employment contracts", "zero fatalities" ~ "zero work-related fatalities"). The verifier is also
  inconsistent: it accepted "Anti-Corruption Policy" ~ "anti-corruption and bribery policies" but
  rejected "Anti-Corruption Policy" ~ "anti-corruption related policies".
- **The test split has now been looked at twice** (M2a, M2b). Further prompt or threshold iteration
  must be judged on val, and the M2 number for the report needs fresh test pools.

## 4e. Clean M2 test (2026-09-13)

Fresh pools (`canon_pools_test2.jsonl`, 81 pools, 811 phrases, 0 shared with the tuning pools, seed
20260914), gold written before any method touched them (123 same-aspect pairs), every setting frozen
from the validation pools (HAC threshold 0.82; verifier variant rules+demos, top-5, floor 0.70).

| method | pairwise P [95 % CI] | pairwise R [95 % CI] | F1 |
|---|---|---|---|
| morph only (no merges) | 1.000 | 0.000 | 0.000 |
| embeddings + HAC @0.82 | 0.467 [0.37-0.58] | 0.463 [0.34-0.59] | 0.465 |
| embeddings propose, LLM verifies | 0.597 [0.49-0.70] | 0.748 [0.63-0.87] | 0.664 |

- Candidate recall holds (115 of 123 gold pairs proposed); the verifier accepts 106 of them but also
  76 non-gold pairs, which is where precision is lost. 629 LLM calls, 313k input tokens.
- The reused-test figure (P 0.733) was optimistic by about 0.14, which is what re-looking at a test
  split costs; the clean figure is the one to quote.
- Verdict: the method is a clear improvement over HAC (F1 +0.20) but **fails the 0.80 precision gate**,
  with the confidence interval now entirely below it. The only way the verdict changes is if the gold
  itself is stricter than human judgement, which the blind spot-check (66 pairs, 10 pools) measures.

## 4f. Graph-RAG proof of concept (2026-09-13)

First 300 gw1000 items, `llm_pre` labels (development numbers), shared zero-shot classifier
(`configs/prompts/action_classifier.md`, gpt-5.6-luna, temperature not applied), k = 3 evidence spans.
Graph arm: aspect → morph group → same company, other years; fused arm: graph first, BM25 over the
company's other-year statements fills to k. Runs `20260913T152226Z` (cached) and `20260913T153019Z`
(`GW_LLM_CACHE=0`, a fresh sample of every call).

| condition | macro-F1 run 1 | macro-F1 run 2 | acc run 1 / 2 | evidence coverage |
|---|---|---|---|---|
| sentence_only | 0.773 | 0.789 | 0.805 / 0.817 | — |
| local | 0.798 | — | 0.829 / — | — |
| cross_year_graph | 0.790 | 0.791 | 0.825 / 0.817 | 0.39 (mean 0.80 spans) |
| cross_year_fused | 0.805 | 0.787 | 0.833 / 0.817 | 0.88 (mean 2.63 spans) |

- **Does not collapse.** No arm is below sentence_only beyond noise (all McNemar p ≥ 0.18), accuracy
  sits at 0.80-0.83, in the range expected given LLM_pre agrees with humans about 86 % of the time.
- **No measurable gain either.** The same prompt re-sampled disagrees with itself on 28 of 300 labels
  and moves macro-F1 by 0.015; run 1's +0.017 (graph) and +0.032 (fused) vanish in run 2 (+0.002,
  -0.002). On the 118 items that received graph evidence, sentence_only vs itself differs on 13 items,
  sentence_only vs graph on 10 (run 1) and 9 (run 2): the evidence effect is below resampling noise.
- **Why so little signal.** 28 of 241 graph spans are the target sentence repeated verbatim in another
  year, which adds nothing; generic aspects pull in off-topic hits (GRI-index-like lines). Fused-arm
  breaks concentrate on no-aspect items (gold `none`), where BM25 noise pushes the model towards an
  action label; one real cross-year break ("started reporting Scope 1 emissions" in 2024 turning a
  disclosure-only sentence into `implemented`) is the relabelling the prompt forbids.
- **Consequences for the harness.** A single cached run hides the classifier's own variance, so every
  RQ1 comparison needs at least 3 uncached repeats per arm (or a temperature-controllable model), with
  flips counted against a sentence_only-vs-sentence_only baseline. Cross-year evidence should skip
  verbatim repeats and not be retrieved for items without an aspect.

## 4g. Calibration on A3CG's own test sets (2026-09-19)

Question: is the shared zero-shot classifier in a sensible range when scored against **human** gold?
A3CG test splits frozen as AC-style snapshots (`gw-data build a3cg`: one row per statement–aspect,
gold aspect given, no-aspect statements as `none`; 3 aspects with two different actions skipped).
`sentence_only` only, since A3CG statements carry no provenance. One run, every call fresh (no cache).

| split | action rows | macro-F1 | micro-F1 | impl. F1 | plan. F1 | indet. F1 | none recall |
|---|---|---|---|---|---|---|---|
| full test | 545 | 0.748 | 0.798 | 0.882 | 0.795 | 0.567 | 0.585 |
| seen avg (3 folds) | 985 | 0.714 | 0.757 | — | — | 0.44–0.59 | 0.56–0.66 |
| unseen avg (3 folds) | 984 | 0.723 | 0.771 | — | — | 0.46–0.61 | 0.59–0.68 |

- **Reference, not a like-for-like comparison.** A3CG's AC sub-task (supervised models) is 59.5–65.7
  full / 51.8–60.5 seen / 21.6–36.5 unseen, but it is scored on pairs whose aspect the model itself
  extracted; here the gold aspect is handed over, and the A3CG release may be in the LLM's training data.
  What the numbers do show: the classifier is not broken, and as a zero-shot model it has no seen/unseen
  gap (A3CG reports the same for its LLM baselines on AAA).
- **The weak class is `indeterminate`**, and its dominant error is towards `implemented` (26–54 rows per
  split), i.e. over-crediting the company, the LLM failure mode A3CG describes. It is also the class
  context is supposed to help (unattributed and hedged statements), so RQ1's bucketed analysis should
  centre on it.
- **`none` recall is only 0.56–0.68**: given a sentence with no aspect, the model still assigns an action.
- **Consistency with the gw1000 dev numbers.** On gw1000 against `llm_pre`, the same classifier scored
  macro-F1 0.77–0.79; against A3CG human gold it scores 0.71–0.75. Similar range, which is weak evidence
  that `llm_pre` is not flattering the classifier much; it does not replace the human-gold rerun.

## 5. Risks

1. **Aspect canonicalisation is the whole ball game.** If "Scope 1 emissions", "direct emissions"
   and "our carbon footprint" do not merge, every cross-year edge is missing. M2 has an explicit gate.
2. **LLM_pre bias.** The graph arm is developed against labels I produced; a model that shares my
   conventions looks better than it is. Mitigation: §3 rules, plus re-running on gold before any claim.
3. **Extraction noise.** `kb/` text has tables, ligature artefacts and merged fragments; metric regexes
   will hit them. M3 gate is a manual precision check, and every node keeps `{file, page, sha256}`.
4. **Latency.** Graph queries are cheap; LLM hops are not. Budget is enforced in the harness
   (`latency_p95` is a reported metric, not an afterthought).
5. **Scope creep.** The graph is a retrieval arm for an existing experiment. If it stops being that,
   it is out of scope.

## 6. Decisions taken (2026-09-12)

| # | Decision | Consequence |
|---|---|---|
| D1 | Store = **DuckDB + networkx**. No Neo4j service. | `DuckDBGraphStore` is the only implementation we build; the Protocol stays so Neo4j remains possible |
| D2 | Build the graph over **eval-set companies only** first | scope is the companies and years touched by `gw1000`; expand only if M2 passes |
| D3 | Aspects outside the annotated 1,000 sentences are extracted by **LLM**, prompted with the A3CG aspect rules | needs a measured extraction-quality gate, see A3 and A8 |
| D4 | The **agentic arm is part of the comparison**, not a side demo | M7 is promoted into the main ablation table; cost and latency are first-class metrics, not footnotes |

## 7. Evidence ledger

Convention for these notes: every design claim is tagged **[cited]** (a paper says so, with the
number), **[measured]** (we measured it on our data) or **[assumed]** (neither yet). No [assumed]
row may reach the report without becoming one of the other two first.

### 7.1 Already checked against papers

| Claim | Tag | Source |
|---|---|---|
| An ESG KG plus graph RAG already exists, so a plain KG is not novelty | [cited] | EmeraldMind, arXiv 2512.11506: EmeraldGraph, 53,748 entities / 59,344 relations from 37 reports; variants EM-RAG, EM-KGRAG, EM-HYBRID |
| Graph-only retrieval does not dominate text retrieval; the hybrid does | [cited] | EmeraldMind Table 5: variants reach 49-77 % coverage vs 19-31 % for the baseline LLM at 77-93 % accuracy; EM-HYBRID is best on overall accuracy, up to 70.59 %, by judging EM-RAG and EM-KGRAG justifications pairwise. Consequence for us: keep a fusion arm, do not bet on graph-only |
| ESG graphs are sparse, company-centred and star-shaped, so reasoning should stay local | [cited] | EmeraldMind section 7.2: Organization nodes are high-degree hubs, average shortest path and diameter are large, global traversal is inefficient. Consequence: company-scoped subgraphs, small hop limits |
| KPI structure carries most of the graph density | [cited] | EmeraldMind Table 4: KPIObservation is about 46 % of entities, reportsKPI about 42 % of edges. Consequence: our Metric and Target nodes are the payload, not an afterthought |
| Sensible starting hyperparameters for graph retrieval | [cited] | EmeraldMind Table 2: top-n 3 nodes per type, similarity threshold 0.2, max 3 hops; EM-RAG top-m 8 chunks |
| Hop limits, schema constraints and traversal heuristics are open questions | [cited] | EmeraldMind, Conclusions and Future Work, names exactly these as future work |
| EmeraldMind has no temporal dimension | [measured] | full-text search of arXiv 2512.11506 returns no hit for temporal, longitudinal, across years, year-over-year or multi-year |
| Canonicalisation should cluster phrase embeddings with complete-linkage HAC and tune the threshold on held-out data | [cited] | CESI (Vashishth et al., WWW 2018, section 6): HAC over cosine similarity, "preferred over other clustering methods because the number of clusters are not known beforehand"; complete linkage because it "gives smaller sized clusters"; "threshold value for HAC was chosen based on held out validation dataset" |
| Canonicalisation is evaluated with macro, micro and pairwise P/R/F1 | [cited] | CESI section 7.2, following Galárraga et al. 2014. Our implementation reproduces the paper's Figure 2 example (P_macro = 2/3, P_micro = 6/7, P_pair = 4/6, R_pair = 4/7) in `tests/test_canonical.py` |
| String normalisation alone barely merges anything | [cited] + [measured] | CESI Table 2: Morph Norm on ReVerb45K scores macro 1.4 / micro 77.7 / pairwise 75.1, GloVe + HAC 56.5 / 82.9 / 75.3. On our graph morph normalisation turns 7,503 aspect ids into 7,319 canonical aspects (184 merges; 7,143 clusters are singletons) |
| Cross-year chain count is not a quality measure for canonicalisation | [measured] | merging aspects fuses chains, so the count can fall while coverage rises: morph normalisation moved chains from 3,932 to 3,906. Canonicalisation is judged on the gold clustering, chains are only descriptive |
| On singleton-heavy gold, macro and micro canonicalisation metrics reward not merging | [measured] | no-merge baseline on our test pools: micro precision 1.0, macro F1 0.949, micro F1 0.938, pairwise recall 0; HAC at 0.82: macro F1 0.946, micro F1 0.944, pairwise P 0.472 / R 0.386 |
| Embedding + complete-linkage HAC alone is not precise enough to merge ESG aspects | [measured] | test pairwise precision 0.472 [95 % CI 0.34-0.61] at the val-selected threshold; 0.281 [0.18-0.40] at 0.74 |
| LLM verification of embedding-proposed merges counters embedding over-generalisation | [cited] | EDC (Zhang & Soh, EMNLP 2024), phase 3: candidates by vector similarity (top-5), LLM verifies "to prevent issues of over-generalization"; CESI observed merging 'place of birth' with 'date of death' |
| Forced binary answers, handwritten matching rules and demonstrations are the levers for LLM pair matching, and no single prompt is best | [cited] | Peeters, Steiner & Bizer, arXiv 2310.11244: prompt must be tuned per model/dataset; in-context learning helped in ~61 % of model/dataset combinations; GPT-4-class models do best with related demonstrations |
| On our pools, LLM verification roughly doubles pairwise F1 over embedding + HAC | [measured] | test pairwise F1 0.742 vs 0.425; precision 0.733 [0.55-0.88] vs 0.472; recall 0.750 vs 0.386 |
| A3CG and its follow-up classify isolated sentences | [cited] | A3CG, ACL 2025, and COGLM, arXiv 2601.21722 |
| Vector RAG is already the right tool for locally answerable queries; GraphRAG targets global sensemaking | [cited] | Microsoft GraphRAG, arXiv 2404.16130: "RAG works well for queries that can be answered with information localized within a small set of records", whereas vector RAG "do not support sensemaking queries ... such as What are the key trends". Settles A2: our queries are local and structured, so community-summary GraphRAG is out of scope |
| Community-summary indexing is expensive | [cited] | GraphRAG: graph indexing with a 600-token window took 281 minutes for the ~1M-token Podcast dataset on a 16 GB VM; datasets were 1669 chunks (~1M tokens) and 3197 chunks (~1.7M tokens); evaluation is LLM-as-judge on comprehensiveness, diversity, empowerment and directness with 72-83 % win rates |
| Graph-only retrieval is bad for specific questions; keep the source text | [cited] | Zhou et al., arXiv 2503.04338, unified graph-RAG study: "for specific QA tasks, retaining the original text chunks is crucial"; methods relying solely on graph structure (G-retriever, ToG, DALK) "perform poorly on most datasets", and G-retriever even reduced accuracy by 14.17 % on one dataset. Consequence: our graph arm returns Statement nodes with their text and page, never bare nodes |
| Graph structure pays off on multi-hop questions | [cited] | Same study: on MultihopQA, DALK improved accuracy 6.57 % and recall 27.94 % over VanillaRAG. Cross-year promise-to-evidence is our multi-hop case |
| The strongest configuration is graph plus vector, not graph alone | [cited] | Same study, Exp.6: their new best method VGraphRAG combines top-k entities and relations with vector-selected communities and chunks, beating RAPTOR by 6.42 % on MultihopQA and 11.6 % on MusiqueQA. Plus EmeraldMind EM-HYBRID. Consequence: a `cross_year_fused` arm is required, not optional |
| Agentic RAG is not universally better, and it is measurably more expensive | [cited] | Ferrazzi et al., arXiv 2601.07711: "neither Enhanced nor Agentic RAG is universally superior"; agentic used 3.3x more input tokens, 1.9x more output tokens and 1.5x more time on average, up to 3.6x more expensive; "a well-optimized Enhanced RAG can match or exceed Agentic performance while remaining more efficient" |
| Where agentic actually helps: intent routing and query rewriting; where it hurts: document selection | [cited] | Same paper: agentic wins on user-intent handling and dynamic query rewriting, but "is not as good as the re-ranking done by Enhanced RAG at selecting just the most meaningful docs"; latency is dominated by LLM calls (45-50 % answer generation, similar share for rewriting, 0-5 % retrieval). Consequence for M7: the agent plans and rewrites, the reranker still picks |
| Missing context and unattributed statements are the dominant error modes | [cited] | A3CG Tables 12 and 13 (ellipsis, ambiguous syntax, modality, negation, unattributed, future dependency) |

### 7.2 Still unsupported, must be settled before or during implementation

| # | Assumption | How it gets settled |
|---|---|---|
| A1 | Traversal beats RRF for same-company same-aspect cross-year lookup | our M4 ablation; a negative result is reportable |
| A3 | Embedding plus clustering canonicalises ESG aspects at purity 0.8 or better | M2 audit of 100 clusters; if it fails, read entity-resolution and aspect-normalisation literature before inventing a method |
| A4 | Development decisions taken on LLM_pre labels survive the switch to human gold | pilot kappa, then re-run; look for work on silver-label evaluation and system ranking stability under label noise |
| A5 | Regex plus unit validation extracts ESG metrics at 0.9 precision | M3 manual check; compare with how ML-Promise and ESGBench extract numbers before writing our own |
| A6 | Retrieved evidence helps specifically the ellipsis and unattributed buckets | bucketed analysis in M4, the prediction is falsifiable |
| A7 | Restated baselines and moved goalposts are detectable and meaningful signals | read the greenwashing measurement literature (Calamai et al. survey, arXiv 2502.07541) for how prior work operationalises them |
| A8 | LLM aspect extraction (D3) on unlabelled corpus sentences is good enough to build edges on | **[measured] passed 2026-09-12** (GPT-6 via Codex): partial F1 0.649, category acc 0.873, no-aspect FP 0.264; measured precision is a lower bound because gold skips enumeration items — needs a human adjudication sample before a corrected figure is quoted. See 05 section 8 |
| A10 | Our category convention for climate-risk aspects (emissions control) matches A3CG | **[measured] it did not; fixed 2026-09-13.** In the A3CG release climate-risk aspects are management (7 of 7) and climate targets/action/decarbonisation/net zero are emissions control. 56 of our aspect-category pairs moved from emissions control to management (TCFD, climate disclosures and scenario analysis follow climate risk by analogy, [project]); the annotator guide and extraction prompt (now v2) state the split. Re-scoring the GPT-6 calibration against the re-mapped gold raised its category accuracy from 0.873 to 0.903 with span metrics unchanged, i.e. part of the earlier disagreement was our convention |
| A9 | An agent that plans and rewrites beats fixed traversal on our task at acceptable cost | M7 under the same harness, with the token and latency multipliers from arXiv 2601.07711 as the expected cost baseline |

### 7.3 Reading queue

1. ~~Microsoft GraphRAG, arXiv 2404.16130~~ — read 2026-09-12, A2 settled (see 7.1).
1b. ~~Zhou et al., arXiv 2503.04338, unified graph-RAG study~~ and ~~Ferrazzi et al., arXiv 2601.07711, Is Agentic RAG worth it~~ — read 2026-09-12.
2. Calamai et al. greenwashing NLP survey, arXiv 2502.07541 (already in the corpus), for A7 and for
   how the field frames verifiability.
3. ML-Promise, EMNLP 2025, for evidence linking inside one document and for its annotation design.
4. A temporal or time-aware RAG reference, to be found, for how others handle year-scoped evidence.
