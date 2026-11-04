# Evidence ledger

Every design claim is tagged **[cited]** (a paper says so, with the number), **[measured]** (we measured
it on our data) or **[assumed]** (neither yet). Nothing tagged [assumed] reaches the report without
becoming one of the other two. Measured rows point to `results.md`, `history.md` or `promises.md`.

## Checked against papers

| claim | tag | source |
|---|---|---|
| An ESG knowledge graph plus graph RAG already exists, so a plain KG is not novelty | [cited] | EmeraldMind, arXiv 2512.11506: EmeraldGraph, 53,748 entities / 59,344 relations from 37 reports; variants EM-RAG, EM-KGRAG, EM-HYBRID |
| Graph-only retrieval does not dominate text retrieval; the hybrid does | [cited] | EmeraldMind Table 5: variants reach 49–77 % coverage vs 19–31 % for the baseline LLM at 77–93 % accuracy; EM-HYBRID is best on overall accuracy, up to 70.59 %. Consequence: keep a fusion arm, do not bet on graph-only |
| ESG graphs are sparse, company-centred and star-shaped, so reasoning should stay local | [cited] | EmeraldMind section 7.2: organisation nodes are high-degree hubs, average shortest path and diameter are large. Consequence: company-scoped subgraphs, small hop limits |
| KPI structure carries most of the graph density | [cited] | EmeraldMind Table 4: KPIObservation is about 46 % of entities, reportsKPI about 42 % of edges |
| Sensible starting hyperparameters for graph retrieval | [cited] | EmeraldMind Table 2: top 3 nodes per type, similarity threshold 0.2, max 3 hops; EM-RAG top 8 chunks |
| Hop limits, schema constraints and traversal heuristics are open questions | [cited] | EmeraldMind, conclusions, names exactly these as future work |
| EmeraldMind has no temporal dimension | [measured] | full-text search of arXiv 2512.11506 finds no hit for temporal, longitudinal, across years, year-over-year or multi-year |
| Canonicalisation should cluster phrase embeddings with complete-linkage HAC and tune the threshold on held-out data | [cited] | CESI (Vashishth et al., WWW 2018, section 6): HAC over cosine, "preferred … because the number of clusters are not known beforehand"; complete linkage "gives smaller sized clusters"; threshold "chosen based on held out validation dataset" |
| Canonicalisation is evaluated with macro, micro and pairwise P/R/F1 | [cited] | CESI section 7.2, following Galárraga et al. 2014. `tests/test_canonical.py` reproduces the paper's Figure 2 example |
| String normalisation alone barely merges anything | [cited] + [measured] | CESI Table 2: Morph Norm on ReVerb45K scores macro 1.4 / micro 77.7 / pairwise 75.1. On our graph it turns 7,503 aspect ids into 7,319 (184 merges; 7,143 singletons) |
| Cross-year chain count is not a quality measure for canonicalisation | [measured] | merging fuses chains, so the count can fall while coverage rises (3,932 → 3,906 under morph normalisation) |
| On singleton-heavy gold, macro and micro metrics reward not merging | [measured] | no-merge baseline on our test pools: micro precision 1.0, macro F1 0.949, micro F1 0.938, pairwise recall 0 |
| Embedding + HAC alone is not precise enough to merge ESG aspects | [measured] | clean test pairwise precision 0.467 [0.37–0.58] at the val-selected threshold |
| LLM verification of embedding-proposed merges counters over-generalisation | [cited] | EDC (Zhang & Soh, EMNLP 2024), phase 3: candidates by vector similarity (top 5), LLM verifies "to prevent issues of over-generalization" |
| Forced binary answers, handwritten rules and demonstrations are the levers for LLM pair matching, and no single prompt is best | [cited] | Peeters, Steiner & Bizer, arXiv 2310.11244: in-context learning helped in about 61 % of model/dataset combinations |
| On our pools, LLM verification raises pairwise F1 over embedding + HAC but still fails the precision gate | [measured] | clean test: P 0.597 [0.49–0.70], R 0.748, F1 0.664 against 0.467 / 0.463 / 0.465; gate was 0.80 precision (`graph.md`) |
| A3CG and its follow-up classify isolated sentences | [cited] | A3CG, ACL 2025, and COGLM, arXiv 2601.21722 |
| Vector RAG is the right tool for locally answerable queries; GraphRAG targets global sensemaking | [cited] | Microsoft GraphRAG, arXiv 2404.16130. Our queries are local and structured, so community-summary GraphRAG is out of scope |
| Community-summary indexing is expensive | [cited] | GraphRAG: indexing a ~1 M-token dataset took 281 minutes on a 16 GB VM |
| Graph-only retrieval is bad for specific questions; keep the source text | [cited] | Zhou et al., arXiv 2503.04338: "for specific QA tasks, retaining the original text chunks is crucial"; graph-only methods "perform poorly on most datasets". Consequence: the graph arm returns statements with their text and page, never bare nodes |
| Graph structure pays off on multi-hop questions | [cited] | same study: on MultihopQA, DALK improved accuracy 6.57 % and recall 27.94 % over vanilla RAG |
| The strongest configuration is graph plus vector, not graph alone | [cited] | same study, VGraphRAG beats RAPTOR by 6.42 % on MultihopQA; plus EmeraldMind EM-HYBRID. Consequence: a fused arm is required |
| Agentic RAG is not universally better, and it is measurably more expensive | [cited] | Ferrazzi et al., arXiv 2601.07711: "neither Enhanced nor Agentic RAG is universally superior"; agentic used 3.3× input tokens, 1.9× output tokens, 1.5× time on average |
| Where agentic helps: intent routing and query rewriting; where it hurts: document selection | [cited] | same paper: "not as good as the re-ranking done by Enhanced RAG at selecting just the most meaningful docs" |
| Missing context and unattributed statements are the dominant error modes | [cited] | A3CG Tables 12 and 13 |
| Verification against evidence needs an explicit "the evidence does not settle it" class, and that class is hard | [cited] | FEVER (Thorne et al., NAACL 2018, arXiv 1803.05355): Supported / Refuted / NotEnoughInfo, Fleiss κ 0.6841; best accuracy 31.87 % when the evidence must be right. Our `unclear` is that class and the outcome rule defaults to it |
| A verdict can be derived from answers to simpler sub-questions | [cited] | ClaimDecomp (Chen, Sriram, Choi & Durrett, EMNLP 2022, arXiv 2205.06938): yes/no subquestions "whose answers influence the veracity of the claim" |
| Declining to answer is a recognised way to cut unsupported output | [cited] | Wen et al., "Know Your Limits: A Survey of Abstention in Large Language Models", TACL (arXiv 2407.18418) |
| Deriving the promise outcome by rule from evidence-level labels cuts over-commitment | [measured] | `promises.md`: 31 % → 8 % of human-unclear promises given a verdict, on held-out rows |
| Fusing a complete ranking with one that covers part of the corpus buries what the partial one cannot see | [measured] | `promises.md`: dense over the sentence-shaped statements only + BM25 over all, RRF k = 60; 1.6 % of the evidence shown came from outside the dense index, and answer statements ranked 1st–3rd on BM25 were cut. From the RRF score itself: 1/61 for first place in one list is less than 2/90 for thirtieth in two |
| A sentence-shape filter removes the sentences that report results, so the knowledge base must be every statement | [measured] | the aspect-extraction gate `looks_like_sentence` rejects "For FY2021, our electricity consumption was 61 kwh per square foot (FY2020: 68 …)"; applied to retrieval it would drop 34 % of statements of five words or more, 20 % for lacking one of its listed verbs and pronouns (`history.md`, 2026-10-04) |
| RQ1's result does not depend on that choice | [measured] | `history.md`, 2026-10-04: a sentence-shaped store against every statement, paired on majority votes, p = 1.00 (same report) and 0.52 (cross year) |
| On held-out promises the rule-based judge on complete evidence gives a verdict on 14 % of the commitments a human calls unclear (31 % before), at unchanged accuracy | [measured] | `promises.md`: 60 held-out promises weighted to 299; accuracy 0.82 (0.70–0.92) on the reported classes; the interval on the 14 % is 2–33 |
| Model annotators calibrated on the group's rows label outcomes at the level of human–human agreement; a second model family gives a real second opinion | [measured] | `promises.md` section 8: 0.875–0.925 against the adjudicated human final on 80 held-out rows, the two humans 0.90 with each other over 137; two instances of one model agreed 79 of 80 times, Fable and Opus 221 of 237, 16 adjudicated |
| With complete evidence a reader cannot tell the outcome of about 31 % of dated commitments, not 49 % | [measured] | same: unclear 30.9 % (21.9–39.0) on trajectory evidence against 48.7 % (39.8–57.7) on the first evidence; different samples, each weighted to its pool |

## Assumptions, and how each was settled

| # | assumption | outcome |
|---|---|---|
| A1 | Traversal beats hybrid retrieval for same-company, same-aspect, cross-year lookup | **[measured] no.** Graph-fused and the sentence-level hybrid are indistinguishable on action F1 (p = 1.00 best vs best); the graph is faster (about 10 ms vs 117–326 ms). `results.md` |
| A2 | Community-summary GraphRAG is the wrong tool for local, structured queries | [cited] settled by arXiv 2404.16130, above |
| A3 | Embedding plus clustering canonicalises ESG aspects at precision 0.8 or better | **[measured] no**, 0.467; with LLM verification 0.597, interval below the gate. The graph keeps morph normalisation. `graph.md` |
| A4 | Decisions taken on LLM pre-labels survive the switch to human gold | [measured] partly. The classifier scored 0.77–0.79 on pre-labels and 0.71–0.75 on A3CG human gold, a similar range; the retrieval conclusions were re-run on human gold before being quoted |
| A5 | Regex plus unit validation extracts ESG metrics at 0.9 precision | superseded: targets are extracted by an LLM with mechanical validation (`promises.md`); no regex extractor was built |
| A6 | Retrieved evidence helps specifically the ellipsis and unattributed buckets | [measured] in part: on human gold the fused arm's gain sat in `indeterminate` (0.559 → 0.683 in the first run) but was not reproduced against the sentence-level hybrid; the classifier cites evidence in 1–11 % of items |
| A7 | Restated baselines and moved goalposts are detectable and meaningful signals | [measured] yes, with care: 10 % of checkable commitments are re-dated or weakened by the human check, but telling a moved goalpost from a missed annual target set again is not reliable, so a re-dated commitment is reported as failed, not as a class of its own (`promises.md`) |
| A8 | LLM aspect extraction on unlabelled corpus sentences is good enough to build edges on | **[measured] passed**: partial F1 0.649, category accuracy 0.903 after convention alignment, no-aspect false-positive rate 0.264 (`graph.md`) |
| A9 | An agent that plans and rewrites beats fixed traversal at acceptable cost | **[measured] not shown**: on RQ2 test, fixed budget → agent +18 / −13 (p = 0.47) with v2 at 1.3× the cost per promise, and the chosen pipeline ties the fixed budget at 2.3× (`agentic.md`, section 6); on RQ1, no paired gain on dev, test not read; over the statement store, not the graph |
| A10 | Our category convention for climate-risk aspects matches A3CG | **[measured] it did not; fixed.** In A3CG climate risk is management; 56 of our pairs were remapped, category accuracy of the extractor rose from 0.873 to 0.903 |
