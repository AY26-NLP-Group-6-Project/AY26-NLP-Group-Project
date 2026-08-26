# Proposal 1 · Energy-Opinion-RAG: Conditional-Stance Opinion RAG for the Southeast-Asian Energy Transition

> Recommendation: 🥈 conditional alternative (data approval first) ｜ 中文版：[README_CN.md](README_CN.md) ｜ [OneDrive paper folder](Useful%20Paper.html)
> One-liner: for questions about nuclear power, SMRs, carbon tax or electricity prices, the system retrieves an **authorised sample of public-platform discourse** plus official documents and reports subjectivity, stance, conditions and frames with evidence, time range and coverage. It does not generalise platform samples to national public opinion.

---

## 1. Problem definition

### 1.1 Formalisation

- **Input**: a natural-language query `q` (may be Singlish or mixed English/Chinese/Malay), optional time window `[t0, t1]`, optional country / subreddit filter.
  Examples: "How do people in the authorised platform sample discuss SMRs?", "人们对碳税涨价有什么意见", "gahmen build nuclear plant can or not".
- **Knowledge base**:
  - `KB_opinion`: Reddit posts and comments (r/singapore, r/malaysia, r/indonesia, r/Philippines, r/nuclear, r/energy, r/ClimateChange, …) with timestamp, subreddit, score, parent id.
  - `KB_fact`: EMA / NCCS / MTI / IAEA / IEA official documents, Wikipedia energy articles, news — the "fact index".
- **Output** (structured + natural-language summary):
  1. an evidence set `E = {e_1..e_k}` relevant to `q` (each with source link, date, subreddit);
  2. core labels: `subjectivity ∈ {objective, opinion}` and, for opinions, `stance ∈ {pro, anti, neutral/unclear}`. `condition_present` and frames are optional multilabel enhancements rather than forcing *conditional* into a mutually exclusive class;
  3. sample-conditioned distributions and time series, always showing sources, date range, retrieved coverage and sample size so retrieval results are not presented as a population poll;
  4. **conflict flags (optional enhancement)** restricted to numerical, dated or explicit policy-state claims—for example, checking “EMA has approved SMR deployment in Singapore” against EMA's statement that no deployment decision has been made;
  5. a coverage statement: which perspectives this answer covers (perspective coverage), so that the majority view does not crowd out minority views.

### 1.2 Why "energy transition" rather than only "nuclear"

The assignment requires ≥10,000 documents and ≥100,000 words. An NUS LKYSPP 2026 working paper reports only **2,157** comments in its Singapore nuclear subset, suggesting that nuclear alone may be too narrow. The provisional domain is therefore the **Southeast-Asian energy transition** (nuclear, solar, EVs, carbon tax, electricity prices/imports, hydrogen and gas dependence), with nuclear as a focus instance. The final scope must be based on a fresh count over authorised data.

### 1.3 Mapping to the grading rubric

| Rubric item | This project |
|---|---|
| KB construction (20) | dual corpus (opinion + fact), cleaning, Singlish handling, comment/passage chunking, `eval.xls` |
| Retrieval (40) | BM25 + dense + RRF + reranker; innovations: Singlish query normalisation, perspective-coverage reranking, time/metadata filtering |
| Downstream (40) | MVP: subjectivity + stance classification and source-qualified opinion summaries; select at most 1–2 of conditions/frames, sarcasm and conflict as ablated enhancements |

---

## 2. Data and knowledge base

### 2.1 Sources (authorisation gate first)

| Source | Access | Use | Notes |
|---|---|---|---|
| Reddit research data | [Reddit for Researchers](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program) (RFR) | candidate `KB_opinion` source | prior approval, university affiliation, ethics approval/exemption, use limits, deletion and no-redistribution conditions apply; Reddit cannot be the committed primary corpus before approval |
| Third-party historical mirrors | [Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift), [Academic Torrents record](https://academictorrents.com/details/186a0f85a52ff4f1b08677cd312423ace9b34976) | availability record only | accessibility is not authorisation; the torrent metadata has no clear licence, so do not use without written approval/compliance clearance |
| HardwareZone and other forums | no default crawl | possible fallback only | check each site's ToS, robots, copyright and research ethics first; public visibility does not itself authorise bulk reuse |
| Official / factual | EMA, NCCS, MTI press releases; IAEA / IEA reports; Wikipedia energy articles | `KB_fact` | public; PDF → text |
| News | CNA / Straits Times public parts, TODAY, Wikipedia citations | `KB_fact` supplement | ST is paywalled — public parts only |
| Generic sentiment / sarcasm | SST-2, IMDB, [SARC](https://arxiv.org/abs/1704.05579), [climatebert/climate_sentiment](https://huggingface.co/datasets/climatebert/climate_sentiment) | training candidates | check each data card/licence and domain mismatch; public access does not automatically permit every training use |
| Singlish resources | [SingBERT](https://huggingface.co/zanelim/singbert) (pre-trained on r/singapore + HWZ), [singlish-to-english-synthetic](https://huggingface.co/datasets/gabrielchua/singlish-to-english-synthetic), [AudioLLMs/Singlish](https://github.com/AudioLLMs/Singlish) | query normalisation, classifier backbone | |

**Size is not yet validated**. The old “~1M comments/year, 30–100k after filtering” estimate was not reproducibly measured and has been removed. Week 1 must first secure RFR or another corpus licence, then run a fixed keyword/de-duplication pipeline and report raw/retained counts, unique authors, time coverage and word count. If ≥10k passages and ≥100k words cannot be demonstrated, switch corpus or topic.

### 2.2 Cleaning and chunking

- Follow the approved retention/deletion plan; remove `[deleted]/[removed]`, bots, comments <5 words and near-duplicates (MinHash), and do not release usernames or a reconstructable raw-text dump.
- A Reddit comment is a natural "passage" — usually no further splitting; long posts > 300 words are split semantically, and `parent_id` is kept for parent-document retrieval (show thread context at answer time).
- Official documents: 200–400-word sections with a title path prepended (contextual chunk header).
- Metadata: `{id, source, subreddit, country, created_utc, score, parent_id, url, lang_flags}`.
- Storage: JSONL (raw) + Lucene / Pyserini index (sparse) + FAISS / Qdrant (dense).

### 2.3 Evaluation set (hard requirement: ≥ 1,000 manually labelled, IAA ≥ 80 %, balanced)

- **Classification set `eval.xls`**: ≥1,000 comments with required fields `text | subjectivity | stance | source | date`; add `condition_present | frames | sarcasm` only after the pilot reaches acceptable IAA.
  - Stratify first by subjectivity and then pro/anti within opinions. Keep objective information separate from neutral/unclear stance. Report the evaluation sampling scheme separately from the corpus's natural distribution.
  - Three annotators independently code a 50–100 item pilot; report raw agreement plus Fleiss' κ or Krippendorff's α. The full set may be divided, but retain a sufficiently large independently double-coded subset before adjudication.
- **Retrieval set `retrieval_qrels.jsonl`**: start with ≥50 queries × pooled top-10 with 0/1/2 relevance and perspective labels; expand to top-30 only if annotation capacity permits.
- **Generation set**: 30–50 queries with human reference summaries (RAGAS answer relevance + human rating).

---

## 3. Baseline level (what we compare against / aim to beat)

| Layer | Current level | Source |
|---|---|---|
| Same-topic study | Authors report 6,853 comments (SG 2,157) and 64% neutral; cite full-text pages/tables before using details such as model design or +17.5pp | [NUS/LKYSPP working paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7005979) |
| Opinion RAG | The 34-benchmark/one-opinion-task count and 79.2% preference are author-reported results | [O-RAG, preprint](https://arxiv.org/abs/2604.12138) |
| Diverse-perspective retrieval | Existing retrievers often fail to cover all known perspectives, motivating explicit coverage evaluation | [BERDS](https://arxiv.org/abs/2409.18110) |
| Evidence conflicts | Supports conflict typing and generator-behaviour evaluation; the unsupported blanket “25% of open-domain questions” wording is removed | [CONFLICTS, preprint](https://arxiv.org/abs/2506.08500) |
| Internal retrieval baseline | BM25 → dense (bge-m3) → hybrid RRF → + reranker, report nDCG@10 / MRR / R@20 at each step | this project v0 |

**Internal v0 baseline** (done by week 3): BM25 (Pyserini) + `bge-m3` + RRF + `bge-reranker-v2-m3`; a fine-tuned `roberta-base` (or SingBERT) two-stage subjectivity→stance classifier; and a reproducible small/8B generator with a simple prompt. Every later innovation is ablated against v0.

---

## 4. Method

### 4.1 Architecture

```
query ─► [optional Singlish / multilingual normalisation + time / country intent parsing]
      ─► sparse BM25 ─┐
      ─► dense bge-m3 ┴► RRF ─► cross-encoder rerank ─► perspective-coverage rerank (MMR / BERDS-style)
      ─► evidence E ─► core classifier (subjectivity → stance; optional condition / frames / sarcasm)
                    ─► optional fact check: retrieve from KB_fact and detect conflicts
                    ─► LLM generation: sample-qualified distribution + summary + citations + coverage statement
      ─► UI (Gradio / Streamlit): pie chart / timeline / evidence cards / source links
```

### 4.2 Retrieval module (Q3 innovations, each ablatable)

1. **Hybrid retrieval + reranking** (course requirement): BM25 + bge-m3 dense + RRF; `bge-reranker-v2-m3` or `jina-reranker-v2`.
2. **Singlish / code-mixed query normalisation (optional)**: begin with rules/prompted rewriting while keeping the original query for a second path. `singlish-to-english-synthetic` has fewer than 1k examples, so it is only an auxiliary set, not evidence that a fine-tuned model will generalise.
3. **Perspective-coverage reranking**: label the top-50 with pro/anti/neutral plus optional condition/frame tags, then use MMR or quotas and a BERDS-style evaluator. Quotas improve answer coverage; they must not be reported as the corpus's natural distribution.
4. **Temporal and metadata retrieval**: `created_utc` filter + time-decay scoring; country / subreddit facets; "before vs after Budget 2025" comparison.
5. **Parent-document / thread context**: feed the parent comment together with the hit, mitigating context-less Reddit replies.

### 4.3 Downstream module (Q5 innovations, ablation required)

1. **Core two-stage classification**: subjectivity → stance; condition/frames are optional multilabel additions. Compare (a) fine-tuned DeBERTa-v3/SingBERT, (b) LLM zero/few-shot and (c) retrieval of similar labelled examples for RAG-augmented classification.
2. **Sarcasm sub-task (optional)**: SARC can provide cross-domain pre-training only. Do not mechanically flip sentiment when sarcasm is detected; validate any treatment on an in-domain labelled subset.
3. **O-RAG-style distribution fidelity**: Wasserstein distance between the output distribution and the corpus distribution — does retrieval skew toward the majority?
4. **Conflict-aware generation (optional)**: extract only numerical, dated and explicit policy-state claims, retrieve from `KB_fact`, then label support/contradiction/insufficient evidence.
5. **Self-check faithfulness**: sentence-level citation back-tracing; unattributable sentences are highlighted.
6. Optional: SenticNet lexicon / concept-level features as a symbolic signal (aligned with the professor and postdoc's group).

### 4.4 Evaluation

- Retrieval: P@5/10, R@20, MRR, nDCG@10 (`ir_measures`); perspective coverage@k; latency.
- Classification: per-stage macro P / R / F1; IAA report.
- Generation: RAGAS faithfulness / answer relevance / context precision; human Likert (3 raters × 30 queries).
- System: QPS, indexing time, GPU memory / cost, scalability discussion.

---

## 5. Acceptance criteria (loose for now; tighten later)

| Item | Minimum (must) | Target |
|---|---|---|
| KB | ≥10k authorised passages and ≥100k words, de-duplicated with full statistics | multiple sources/time windows plus ≥2k fact passages |
| Eval set | ≥1,000 `eval.xls` rows, main-task raw agreement ≥0.80, de-duplicated and stratified; IAA reproducible on an independently recoded subset | κ/α ≥0.7; retrieval qrels for ≥50 queries |
| Retrieval | hybrid > BM25 alone and > dense alone (nDCG@10 +≥ 3 pt); ≥ 1 innovation with positive ablation | ≥ 2 positive innovations; coverage@10 +≥ 10 pt |
| Classification | subjectivity F1 ≥0.75; stance macro-F1 ≥0.60 | stance ≥0.70; optional modules report their own metrics |
| Generation | RAGAS faithfulness ≥0.75; every conclusion has evidence plus sample qualification | ≥0.85; report conflict precision only if that module is implemented |
| Performance | end-to-end ≤ 5 s per query (local 8B model) | ≤ 3 s |
| UI | Gradio / Streamlit demo with 5 timed queries | timeline + distribution chart + evidence cards |
| Report | answers Q1–Q5 with ablation tables, before/after example queries, failure cases | slides included |

---

## 6. Citation audit and paper roles ([OneDrive paper folder](Useful%20Paper.html))

| Verified source | Use and boundary |
|---|---|
| [O-RAG](https://arxiv.org/abs/2604.12138) (preprint) | Core motivation plus coverage/fidelity/fairness and distribution metrics; identify exact figures as author-reported. |
| [DIVERGE](https://arxiv.org/abs/2602.00238) (preprint) | Viewpoint-conditioned retrieval enhancement; multi-agent execution is beyond the MVP. |
| [BERDS](https://arxiv.org/abs/2409.18110) / [PerSphere](https://arxiv.org/abs/2412.12588) | Direct support for perspective retrieval and summarisation evaluation. |
| [CONFLICTS](https://arxiv.org/abs/2506.08500) (preprint) | Conflict taxonomy and behavioural evaluation, not a universal open-domain conflict-rate estimate. |
| [Code-switching survey](https://arxiv.org/abs/2510.07037) | Supports normalisation-vs-multilingual-embedding choices. The [MNSC/Singlish work](https://arxiv.org/abs/2501.01034) focuses on speech/audio and is not direct evidence for text retrieval. |
| [Retrieval-augmented financial sentiment](https://arxiv.org/abs/2310.04027) | A transferable classification template; finance-domain gains are not expected gains for this task. |
| [LACA](https://arxiv.org/abs/2508.09515) | ACL 2025 cross-lingual ABSA pseudo-data method; an analogy, not evidence that Singlish pseudo-labelling will work. |
| [SARC](https://arxiv.org/abs/1704.05579) | Sarcasm pre-training candidate with a substantial domain gap. |
| [NUS/LKYSPP working paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7005979) | Same-topic background and scale reference; check the full text before citing label procedures, frames or exact outcomes. |
| [Shared OneDrive paper folder](../Common%20Useful%20Paper.html) | General RAG, evaluation, chunking, LiveRAG and graph-method background. |

---

## 7. Challenges

1. **Data authorisation is the go/no-go gate**: do not collect Reddit at scale or commit to this topic before RFR/other written permission and institutional ethics approval/exemption.
2. **Conditional language**: use `condition_present` as a multilabel annotation rather than a mutually exclusive stance; pilot 50–100 items and iterate twice.
3. **Neutral/informational dominance**: stratification is allowed, but the corpus's natural distribution must be reported separately.
4. **Sarcasm, Singlish and code-mixing**: analyse as subsets first; promote them to model modules only if a pilot shows value and capacity permits.
5. **Opinion/fact boundary**: restrict conflict checking to numerical, policy-state and dated claims.
6. **Compute and sensitivity**: favour reproducible small-model baselines; no user profiling, and follow RFR anonymisation, retention, deletion and no-redistribution conditions.

---

## 8. Other notes

- **ToS / licensing**: follow Reddit's [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy), [data-access guidance](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data) and RFR approval terms. Removing usernames does not replace access authorisation. Record reuse/storage terms for official documents too.
- **Overlap risk (> 30 % = zero marks)**: past projects commonly do "Reddit crypto / movie sentiment"; this project differs in domain (energy transition), task (conditional stance + coverage + conflicts) and data (dual corpus + Singlish). Do not share implementation details.
- **Suggested split (5–6 people)**: KB team 2 (crawling / cleaning / annotation coordination); retrieval team 2 (indexing / hybrid / reranking / Singlish / coverage); downstream team 2 (classifiers / generation / conflicts / RAGAS / UI). Everyone annotates (~400 items each, with overlap).
- **Timeline (deadline 2026-11-07)**:
  - W1–2 (≈13 Sep): confirm RFR/other corpus authorisation and ethics status; quantify only authorised samples, run a 50–100 item pilot and build v0. Switch corpus/topic immediately if approval or size fails.
  - W3–4: v0 end-to-end + UI; full annotation starts.
  - W5–7: retrieval + downstream innovations, ablations; annotation done, IAA computed.
  - W8–9: RAGAS / human evaluation, failure analysis, performance tests.
  - W10: report + slides + zip packages (KB, query results, eval, code README).
- **Follow-on research**: if publishable data rights and rigorous evaluation are secured, the dataset/system could support later research. Do not claim “first” without a systematic novelty search.

---

## 9. Links

- SenticNet projects (climate resilience → public views on nuclear): https://sentic.net/projects
- Reddit for Researchers: https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program
- BERDS code / data: https://timchen0618.github.io/berds/
- CONFLICTS dataset: https://github.com/google-research-datasets/rag_conflicts
- SingBERT: https://huggingface.co/zanelim/singbert ; Singlish→English synthetic data: https://huggingface.co/datasets/gabrielchua/singlish-to-english-synthetic
- Official Singapore nuclear material: [EMA 2025 feasibility/safety study](https://www.ema.gov.sg/news-events/news/media-releases/2025/ema-to-conduct-study-on-safety-technical-feasibility-of-advanced-nuclear-energy-technologies), [EMA 2026 explainer](https://www.ema.gov.sg/news-events/news/feature-stories/2026/understanding-advanced-nuclear-energy-technologies-how-singapore-is-assessing-its-potential)
- Tooling: Pyserini, FAISS / Qdrant, sentence-transformers (bge-m3), ir_measures, RAGAS, vLLM / Ollama, Gradio
