# Proposal 3 · Greenwash-RAG: Evidence-Grounded, Cross-Year Tracking of SGX Sustainability Claims

> Recommendation: 🥉 highest ceiling / highest risk (directly aligned with the ACL 2025 work of the professor and postdoc's group) ｜ 中文版：[README_CN.md](README_CN.md) ｜ [OneDrive paper folder](Useful%20Paper.html)
> Revised 2026-09-10 after a close reading of the primary literature and a data-acquisition pilot.
> One-liner: given a company plus a sustainability commitment or aspect, the system retrieves the company's own report evidence across years, labels each statement implemented / planning / indeterminate, and returns a page-cited commitment timeline; the research question is whether that retrieved evidence **changes and improves** A3CG classification relative to sentence-only input. Visual pages and external evidence are enhancements. The output is evidence-backed risk screening, not a definitive verdict that a company is greenwashing.

---

## 0. Goals at a glance

### 0.1 The user problem: who it is for and what it solves

SGX requires every mainboard issuer to publish an annual sustainability report (Listing Rule 711A), typically 40–150 pages each. Analysts, investors, regulators and journalists routinely need to answer questions like:

> "Company X committed to an emissions target in 2021 — was it ever delivered, and on which pages is the evidence?"

Answering by hand means reading 3–4 years of reports and locating the relevant passages inside heavily templated ESG prose. The system's target output (illustrative — company and quotes are fictional):

```
2021  p.34  "we aim to reduce ... by 2025"            → planning
2022  p.41  "we remain committed to this target"      → planning
2023  p.38  "we continue to explore options"          → indeterminate
2024  —     aspect no longer mentioned
⚠ Risk signal: commitment stayed planning / indeterminate for 3 years with no implemented evidence (assistive screening, not a verdict)
```

Existing methods handle this poorly for three reasons:

1. **Sentence-level judgement fails.** A3CG-style models read one sentence at a time. "We have achieved this target ahead of schedule" does not say what "this target" is; "Industry players are expected to reduce plastic packaging" does not say whether it is the company's own action or a restated regulation. These are exactly the top failure modes A3CG itself reports: *ellipsis* for supervised models and *unattributed statements* for LLMs.
2. **ESG reports are heavily templated.** Sentences like "We are committed to reducing our carbon footprint" appear near-verbatim across dozens of companies, so dense retrieval without a company filter is likely to rank other companies' passages first (a hypothesis to be measured).
3. **Nobody looks across years.** EmeraldMind, ML-Promise and A3CG all lack a cross-year comparison (see §1.4).

### 0.2 Research questions: where the novelty is

- **RQ1**: Does adding retrieved report-internal context make aspect–action classification more accurate than sentence-only input, on seen and unseen categories?
- **RQ2**: Can cross-year retrieval correctly reconstruct a commitment's trajectory (planning → implemented, stuck at planning, weakened, dropped)?
- **RQ3**: Does company/year metadata filtering reduce cross-company retrieval errors?

The user feature in 0.1 only works if all three have answers, so the research and the system are the same piece of work, not two. **Explicitly out of scope**: any company-level "is this greenwashing" verdict.

### 0.3 How it is quantified (details in §4.4 and §5)

- **RQ1**: ΔF1 of each evidence condition over sentence-only, plus flip analysis and a significance test. **This is the primary acceptance criterion.**
- **RQ2**: trajectory exact-match rate and transition F1.
- **RQ3**: ablations on nDCG@10 and a custom wrong-company@10.
- The course's hard requirements (KB size, IAA, RAGAS, latency) are reported as usual.

---

## 1. Problem definition

### 1.1 Formalisation

- **Input**: `(company, claim_text)` or `(company, aspect)` (e.g. "DBS's progress toward carbon neutrality"), optional year.
- **Knowledge base**:
  - `KB_report`: 2020–2025 sustainability reports / ESG chapters of SGX-listed companies (PDF → text passages + page images).
  - `KB_external`: news (CNA, Business Times public parts, Eco-Business), regulatory documents (SGX RegCo, MAS, NEA carbon tax), NGO reports.
- **Output**:
  1. evidence set (report passages / page screenshots + external articles) with source, page, year;
  2. A3CG-style labels: first decide whether an aspect–action pair exists; if so, extract the `aspect` span and assign `action ∈ {implemented, planning, indeterminate}`. *Indeterminate* means the action state cannot be established from the text; it is **not proof of greenwashing**;
  3. report-internal consistency and cross-year change; external `supports / refutes / not_enough_info` is an optional AVeriTeC-style extension;
  4. risk signals such as vague wording, absent quantified target/year and internal inconsistency, each with page citations and an “assistive screening, not a verdict” notice.

### 1.2 Why it is worth doing

- [A3CG](https://aclanthology.org/2025.acl-long.723/), an ACL 2025 paper from the professor and postdoc's group, provides the aspect–action scheme, data and seen/unseen protocol. **Every published result on A3CG — including the group's own January 2026 follow-up — classifies a single isolated sentence.** Nobody has yet asked whether retrieved report-internal or cross-year evidence changes the action label. That question is our contribution; see §1.4.
- SGX sustainability and climate-disclosure rules provide locally relevant longitudinal documents. Since the rules evolve, cite the [current SGX Rulebook](https://rulebook.sgx.com/rulebook/711b) and [reporting guide](https://rulebook.sgx.com/rulebook/practice-note-7f-sustainability-reporting-guide), not only a static 2016/2022 summary. Table/chart pages can support a controlled visual-retrieval enhancement.
- Hits both the "climate resilience (greenwashing detection)" and "finance" lines on the SenticNet project page.

### 1.3 Mapping to the grading rubric

| Rubric item | This project |
|---|---|
| KB (20) | PDF crawling / parsing (text + page images), section / page chunking, company / year metadata, `eval.xls` |
| Retrieval (40) | MVP: text hybrid retrieval + company/year filters + reranking; enhancement: visual retrieval/fusion on a controlled table/chart subset |
| Downstream (40) | MVP: A3CG-style pair/no-pair, aspect span, action classification and evidence explanation; external fact-checking only if annotation capacity permits |

### 1.4 Positioning against prior art (revised 2026-09-10)

The earlier claim that "our quick search found no exactly equivalent system" is **withdrawn**. A systematic search found the following, and the final report must cite all four or the novelty search will read as incomplete:

| Prior system | What it already does | Overlap with our original MVP |
|---|---|---|
| **EmeraldMind**, ACM Web Conference 2026 ([arXiv 2512.11506](https://arxiv.org/abs/2512.11506)) + **EmeraldApp** demo | End-to-end domain RAG for greenwashing detection: `EmeraldDB` (vectorised ESG report chunks) + `EmeraldGraph` (KG, 53,748 entities / 59,344 relations from 37 reports); verdict `greenwashing / not / abstain` **plus an evidence-grounded justification**; EM-RAG / EM-KGRAG / EM-HYBRID ablations; coverage-aware evaluation | **High** — this is our original MVP |
| **ML-Promise**, EMNLP 2025 ([main.1028](https://aclanthology.org/2025.emnlp-main.1028/)) | Promise Identification / Actionable Evidence / Clarity / Timing over ESG reports in 5 languages; evidence located **within the same document**; textual *and* image RAG baselines; κ 0.60–0.96 | **High** — this is "report-internal evidence checking" |
| **SwissText 2025** ([swisstext-1.3](https://aclanthology.org/2025.swisstext-1.3/)) | ClimateBERT specificity + Sentence-BERT internal claim substantiation as greenwashing hints over 150 German DAX reports | **High** for the rule-based risk signals |
| **COGLM**, [arXiv 2601.21722](https://arxiv.org/abs/2601.21722) (Jan 2026, same group as A3CG) | Contrastive + ordinal + gated LoRA fine-tuning for cross-category robustness on A3CG | **Total** — do not propose contrastive/ordinal objectives as our innovation |

**What is still open, and what we should therefore claim:**

1. **Retrieval-conditioned aspect–action classification.** A3CG and COGLM both classify isolated sentences. A3CG's own error analysis says the dominant supervised failure is *ellipsis* (missing context) and the dominant LLM failure is *unattributed statements* — both are exactly what company-scoped retrieval supplies.
2. **Cross-year / longitudinal claim tracking.** ML-Promise is single-year (2021+); EmeraldMind has no temporal dimension; A3CG spans 2017–2022 but never compares across years.
3. **An SGX longitudinal corpus with page-level provenance.** A3CG's own report list is not published (§2.1), so an independently built 2020–2025 SGX corpus with `{company, year, page, section}` metadata is a genuine artefact that also extends past A3CG's 2022 cut-off.

**Headline experiment.** One aspect–action classifier under four evidence conditions — `sentence-only → +local context → +same-report retrieved evidence → +cross-year retrieved evidence` — reported on our held-out self-annotated SGX 2023–2025 set, where every item carries `{company, year, page}` provenance; seen/unseen is obtained by mapping A3CG's per-fold category splits onto that set (see §4.4). A3CG itself releases isolated sentences with no source document, so their context cannot be retrieved — A3CG is used for training and the sentence-only baseline only. Retrieval quality (P@k, R@k, MRR, nDCG@10) is the independent variable; action F1 is the dependent one. Neither EmeraldMind, ML-Promise nor COGLM has answered this.

The course's 30 %-overlap disqualification rule concerns other student projects, not published research, so none of the above is a compliance problem — it is a credibility problem, and it is solved by citing them and stating the delta.

---

## 2. Data and knowledge base

### 2.1 Sources

> Done.

| Source | Access | Use | Notes |
|---|---|---|---|
| SGX-listed sustainability reports | company IR pages and SGXNet; third-party indexes for discovery only | `KB_report` | **Pilot verified 2026-09-10: 5/5 reports downloaded first try, no auth, no captcha.** SGXNet PDFs are directly fetchable at `https://links.sgx.com/1.0.0/corporate-announcements/<ID>/<file>.pdf`; `api.sgx.com/announcements/...` returns `Missing Authentication Token`, so enumerating announcements needs the SGX web UI (Playwright) or per-company IR crawling. `sgx.com/robots.txt` is `Allow: /` with no crawl-delay — rate-limit ourselves anyway. Public visibility does not automatically permit bulk redistribution; save source URL/date, robots/terms and report copyright, and release only permitted derivatives |
| A3CG dataset | **[keanepotato/a3cg_greenwash](https://github.com/keanepotato/a3cg_greenwash)** (the repo cited in the paper itself) | train/compare the aspect–action classifier | **Use this repo, not `SenticNet/greenwashing-detection`.** It ships the dataset *plus* the GRACE implementation, configs, eval shell scripts, preprocessed BIO data and `results/*_test_outputs.csv` prediction dumps; trained checkpoints are on HF under `keentomato/a3cg_greenwash_grace_f{1,2,3}`. The "code coming soon" note is stale for GRACE (other model families are still being cleaned up). **Two gaps: no LICENSE file on either repo, and the company/year list promised in the paper's footnote 2 is absent — so their 1,679-report source corpus cannot be reconstructed.** Email the first author about both |
| ClimateBERT data | [climatebert/environmental_claims](https://huggingface.co/datasets/climatebert/environmental_claims), `climate_detection`, `tcfd_recommendations`, **`climate_specificity`** | claim-detection candidates; `climate_specificity` feeds the vagueness risk signal | All are **CC-BY-NC-SA-4.0** (non-commercial + share-alike) — declare this. Verified sizes: environmental_claims 2,117/265/265 with only **25 % positives** (train 532/2,117); climate_detection 1,300/400; tcfd_recommendations 1,300/400 (5-way); climate_specificity 1,000/320 |
| External news / regulation | Eco-Business, CNA, SGX RegCo, MAS, NEA public pages | optional `KB_external` | check each site's crawl/reuse terms; paywalled or unstable content is not part of the core KB |
| ML-Promise | Google Drive folder ("PromiseEval Dataset") linked from `MLpromise.nlpfin.com` | related-work comparison; optional promise/evidence labels | accessible; English portion is only ~200 instances and there is no SGX coverage |
| Kaggle S&P 500 ESG reports | [S&P 500 ESG reports](https://www.kaggle.com/datasets/jaidityachopra/esg-sustainability-reports-of-s-and-p-500-companies) | extra training / background | page exists but contents were not readable without login — treat as optional, never as a dependency |
| GreenClaims (Fornasiero) | via the EmeraldMind paper | citation only | the only third-party-verified greenwashing label set that exists — but **91 claims, 51 usable**. Too small to build on |

**Size — now measured, not estimated.** A 5-report pilot (SGX small/mid-cap FY2024) gave **219 pages / 63,035 words**, i.e. **12,607 words and 43.8 pages per report**, and ~57 % of pages contained a detected table.

| Threshold | Reports needed |
|---|---|
| ≥100,000 words | **≈ 8** — trivially met |
| ≥10,000 chunks @ 300 words (~42 chunks/report) | **≈ 240** ← the binding constraint |
| ≥10,000 chunks @ 200 words | ≈ 160 |

→ **Target ~60–80 companies × 3–4 years ≈ 240 reports ≈ 10,500 pages ≈ 3.0 M words.** The pilot was deliberately small/mid-cap; large caps (DBS, CapitaLand, Sembcorp) run 80–150 pages, so a mixed-cap sample reaches the threshold with fewer reports. Re-extrapolate after the week-1 90-report pilot using the measured parse-failure rate. Visually index a capped table/chart subset (see §4.2), not every page.

### 2.2 Parsing and chunking

- Text: `pymupdf` / `marker` extraction + tables via `camelot` / `pdfplumber`; 200–400-word chunks by heading hierarchy with a "company | year | section" contextual header.
- Visual: render each page at 150 dpi; encode with ColQwen2.5 / Qwen3-VL-Embedding; dual index (page level + text-chunk level); when fusing, expand a page hit into its chunks.
- Metadata: `{company, ticker, sector, year, page, section, has_table, has_chart}`.
- **Expect PDF-extraction noise and tolerate it.** The ACL-published A3CG text still contains artifacts such as `"energy -efficient"` and `"Goals for the next 3 -5 years  (Medium - to long -term goals)"`. This is direct evidence that comparable noise in our own pipeline is acceptable — do not over-engineer normalisation.

### 2.3 Evaluation set (≥ 1,000 rows, IAA ≥ 80 %)

- **`eval.xls`**: ≥1,000 SGX-report sentences including environmental claims and controls. Label `has_aspect_action` and `aspect_span`; assign `action ∈ {implemented, planning, indeterminate}` only when a pair exists. `specificity` is optional. Every row must also record: `{company, year, page}` provenance (the evidence-conditioning experiment retrieves context from it); the A3CG aspect category (for the seen/unseen mapping); and optionally an A3CG failure-mode tag (ellipsis / ambiguous syntax / modality / negation / unattributed / future dependency, for bucketed analysis). About **33.2 % of A3CG statements contain no aspect–action pair** (verified: 666/2,004), so retain a no-pair class instead of balancing only the three actions.
- **A3CG reports no inter-annotator agreement figure at all.** Its protocol used 5 annotators + 3 verifiers *all doing doctoral or postdoctoral research in sustainability*, trial rounds to ≥95 % proficiency, 3-day disagreement resolution and a 20 % verifier audit with full re-annotation above a 5 % error rate. That is a labelling *protocol*, not evidence that ≥80 % IAA is attainable by us. **Meeting the course's ≥80 % requirement is entirely on us and is the project's dominant schedule risk.**
- **Staged annotation protocol** (splits one hard decision into three easy ones):
  - **Round A** — sentence-level `has_aspect_action` (binary). Fast, high agreement, and ~33 % of items are negatives, so this alone is a legitimate labelled dimension.
  - **Round B** — for positives, present candidate spans **pre-extracted by the fine-tuned A3CG model** and have annotators accept / reject / edit rather than write spans from scratch. Verification agreement is far higher than free-annotation agreement, and the brief explicitly permits "manually labelled **or verified**" records.
  - **Round C** — action label given the accepted span (3-way).
  - Report agreement **per dimension**: raw agreement + κ for the binary and action decisions; token-level F1 / overlap for spans (κ is not meaningful for spans).
  - Two pilot rounds of 50 items before scaling — A3CG's own protocol did exactly this. Disagreement concentrates almost entirely on `implemented` vs `indeterminate`; copy A3CG's `indeterminate` sub-rules verbatim into the guideline (hedging without assurance of follow-through; figure disclosure without a claimed improvement; listing responsibilities without an explicit sustainability link).
- **External verification set (optional)**: add claim + evidence + `supports/refutes/NEI` only after the core 1,000 items are complete and evidence is reliably available. Do not select only large companies to guarantee refutations and then claim population-level performance.
- **Retrieval qrels**: start with ≥50 queries × pooled top-10. Report the naturally occurring table/chart subset separately rather than forcing one-third of answers to be visual.

---

## 3. Baseline level

Numbers below were read out of the papers during the 2026-09-10 review, not paraphrased.

| Layer | Current level | Source |
|---|---|---|
| Aspect–action classification (A3CG) | 1,679 SGX reports (2017–2022), 2,004 statements, 2,723 aspect–action pairs (implemented 1,459 / indeterminate 885 / planning 379), 10 categories + no-aspect. **AAA F1 — full dataset 67.1–71.3 (best CONTRASTE 71.33); seen avg 61.96–67.47; unseen avg 41.12–47.51 (best GRACE 47.51).** Sub-task **AC (action) is harder than ATE everywhere**: AC full 59.5–65.7, seen 51.8–60.5, **unseen 21.6–36.5**. LLMs trail badly (best Claude 3.5 Sonnet+FS: 42.03 unseen). Paper explicitly states it is **not** definitive greenwashing detection | [A3CG, ACL 2025](https://aclanthology.org/2025.acl-long.723/), Tables 2 and 14 |
| **Current SOTA on A3CG** | **COGLM (LoRA + contrastive + ordinal + gating + MetaGradNorm): 72.40 full / 67.59 seen / 49.04 unseen.** A 220 M T5 beats every 7–8 B LoRA decoder they tried and beats GPT-4o / Claude 3.5 / LLaMA-3-70B on unseen. Gains are non-monotonic and highly hyper-parameter-sensitive. **Purely model-side — no retrieval, no document context, no temporal dimension** | [arXiv 2601.21722](https://arxiv.org/abs/2601.21722) (preprint, Jan 2026, same group as A3CG) |
| Greenwashing RAG system | EmeraldMind: EM-KGRAG 93.55 % zero-shot accuracy at 60.78 % coverage on GreenClaims (51 claims); EM-RAG 62–77 % coverage on the 620-item semi-synthetic EmeraldData. Built from only **37** ESG reports; claims are LLM-generated and LLM-labelled; no aspect–action granularity, no temporal dimension, no SGX | [EmeraldMind, WWW 2026](https://arxiv.org/abs/2512.11506) |
| ESG PDF QA difficulty | RAG baseline on 12 reports / 119 QA pairs: **EM 21.0 %, string F1 55.4 %, numeric accuracy@±2 % 45.3 %, recall@5 70–80 %** — numeric/table grounding is the failure mode | [ESGBench, ICAIF 2025 workshop](https://arxiv.org/abs/2511.16438) |
| Environmental-claim detection | Expert-annotated binary environmental-claim data plus a ClimateBERT baseline; the unsourced “F1≈0.8+” shorthand is removed | [ClimateBERT environmental claims](https://arxiv.org/abs/2209.00507) |
| Greenwashing NLP landscape | *"Crucially, no dataset of verified greenwashing cases currently exists."* Recommends third-party judgments over subjective annotation, and **decomposed pipelines supporting human oversight and traceable reasoning** — i.e. it endorses our architecture | [Calamai et al. survey](https://arxiv.org/abs/2502.07541) (v2, Jan 2026) |
| Visual document retrieval | ~26 k pages, 3,099 human-verified queries, 6 languages; visual retrievers beat text, hybrid context improves answers, fine-grained visual grounding still fails. Public record does not establish “ACL 2026 accepted” | [ViDoRe V3, preprint](https://arxiv.org/abs/2601.08620) |
| RAG fact-checking | Cite the 2025 overview/winner paper for the winning system and efficiency; the 2024 AIC-CTU paper is a predecessor, not the 2025 winner paper | [overview](https://aclanthology.org/2025.fever-1.15/), [winner paper](https://aclanthology.org/2025.fever-1.22/), [2024 predecessor](https://arxiv.org/abs/2410.11446) |
| Internal v0 | text BM25 + bge dense + RRF + reranker; classifier = A3CG-fine-tuned encoder; verification = LLM + top-5 external evidence | this project |

---

## 4. Method

### 4.1 Architecture

```
(company, claim / aspect, year?) ─► query construction (company aliases, aspect synonyms)
   ─► text hybrid retrieval (BM25 + bge-m3 + RRF) ─┐
   ─► optional visual page retrieval (ColQwen / Qwen3-VL-Emb) ┴► cross-modal fusion ─► rerank
   ─► evidence: report passages + optional page screenshots / external articles
   ─► classification: aspect–action (A3CG fine-tuned model / LLM + RAG)
        └─ evidence-condition switch: none | local | same-report | cross-year   ← headline ablation
   ─► optional external verification: NLI / LLM → supports / refutes / NEI
   ─► greenwashing-risk explanation (page citations; vague wording highlighted; target / year / number checks)
   ─► UI: company picker + claim input + evidence page thumbnails + risk cards
```

### 4.2 Retrieval innovations (Q3)

1. Hybrid retrieval + cross-encoder reranking (course requirement).
2. **Company / year metadata filtering + cross-year comparison retrieval** ("was the 2022 target quietly changed in 2024?" → timeline retrieval). This is the most defensible novel retrieval component and maps directly onto the brief's "timeline and metadata search" bullet — promote it ahead of visual retrieval.
3. **Visual page retrieval (enhancement)**: fuse only on a **capped** table/chart subset. Since ~57 % of pilot pages contain a table, "the natural table/chart subset" would grow to half the corpus — so cap it explicitly at **≤1,200 pages**. Budget: ColPali-class models emit ~1,030 vectors × 128 d per page ≈ 260 KB/page in fp16, so 1,200 pages ≈ 0.3 GB (a full 10 k-page index would be ~2.7 GB and ~2–4 h of encoding on a 4090-class GPU). Ablate text-only / visual-only / fused without making a full-page visual index the minimum deliverable.
4. **Query expansion**: aspect synonym table (A3CG aspect categories) + HyDE hypothetical passages.
5. Contextual chunk headers vs. late chunking.

### 4.3 Downstream innovations (Q5)

1. **Evidence-conditioned aspect–action classification (headline).** The same classifier under `sentence-only / +local context / +same-report retrieved / +cross-year retrieved`, on our own provenance-tagged SGX set (seen/unseen via the A3CG fold category mapping). This is the experiment nobody has run; everything else is supporting.
2. **Cross-year consistency checking.** Retrieve the same company's claims for the same aspect across years and report label transitions (`planning → implemented`? target weakened? claim dropped?). Report-internal first; external AVeriTeC-style verification is a second-stage option.
3. **Greenwashing-risk-signal explanation**: rules (no number/year, vague wording, `climate_specificity`) plus cited LLM explanation. Note in the report that SwissText 2025 already established the specificity/internal-substantiation signal — our delta is applying it per aspect–action pair with page-level provenance, and always calling it a risk signal, never a company-level verdict.
4. **Cross-category generalisation experiment**: train on A3CG fold-k's seen categories, test on the items of our eval set that fall in fold-k's unseen categories, and check whether RAG context improves unseen generalisation. It is a useful course experiment, not a promised publication result. Optional bonus: exact-match A3CG sentences inside our 2020–2022 corpus to recover context for part of A3CG.
5. **Do not claim contrastive / ordinal / gated objectives as an innovation** — COGLM (arXiv 2601.21722, same group, Jan 2026) already published exactly that on exactly this dataset. Reproducing it as a baseline is fine and useful; presenting it as ours is not.
6. Optional: SenticNet concept-level features as a symbolic signal (aligned with tools used by the professor and postdoc's group).

### 4.4 Evaluation

| Layer | Answers | Metrics | Data |
|---|---|---|---|
| KB | is the corpus big and clean enough | reports, chunks, words, types, parse success rate | ~240 SGX reports |
| Retrieval | RQ3 | P@5, R@10, MRR, nDCG@10; **wrong-company@10** (share of top-10 passages from the wrong company, custom); table/chart subset reported separately | ≥50 queries in three types — company-specific claim lookup / cross-year same-aspect lookup / generic; pooled top-10 manual relevance |
| Classification (absolute) | does the system work at all | has_pair F1, span token-F1, action macro-F1 + per-class F1 + accuracy, joint AAA F1 | self-built `eval.xls` |
| **Classification (headline)** | **RQ1** | **ΔF1** of each evidence condition over sentence-only; **flip analysis** (share of predictions that change once evidence is added, and the net of wrong→right minus right→wrong); McNemar test or bootstrap 95 % CI | same set, every row with provenance |
| Bucketed analysis | which errors evidence actually fixes | Δ per A3CG failure mode (six types) | failure-mode tags on eval rows |
| Cross-year trajectories | RQ2 | trajectory exact-match rate, transition F1 | ~60 (company, aspect) × ≥3-year manually labelled trajectories |
| Generation | is the explanation trustworthy | RAGAS faithfulness / answer relevance / context precision; **citation precision** (manually check 50 answers: does the cited page support the claim); optional human Likert | system outputs |
| External verification (optional) | — | 3-way macro-F1; Ev2R-style evidence recall (LLM-judged) | only if implemented |
| System | is it usable | per-stage p50/p95 latency, indexing time, visual-index GPU memory/disk, 5 timed queries | — |

- **Name the metric precisely** — AAA (joint pair F1) vs ATE vs AC, micro vs macro, gold-span vs joint extraction. Mixing them is the fastest way to look like the numbers were not understood.
- **How seen/unseen is done**: reuse A3CG's three fold category splits — train on fold-k's seen categories, test on our eval items in fold-k's unseen categories. `eval.xls` therefore needs an aspect-category column (cheap).
- **The headline is the Δ, not the absolute F1**: even if overall scores are modest, a cleanly reported Δ with confidence intervals still stands as a result.
- **The bucket prediction is falsifiable**: evidence should help ellipsis / unattributed (missing context, missing attribution) and should not help negation / modality (the information is already in the sentence). The opposite outcome would itself be a useful finding.

---

## 5. Acceptance criteria

**The previous classification targets were above published SOTA and have been corrected.** The old row asked for action macro-F1 ≥0.70 seen / ≥0.55 unseen (target 0.78 / 0.65); A3CG's own AC scores are 51.8–60.5 seen and 21.6–36.5 unseen, and the current SOTA on the joint task is 67.6 seen / 49.0 unseen. Note that A3CG's AC is already measured *after* aspects are correctly identified, which is close to "given a gold span" — so fixing the span does not make the task materially easier. **Absolute classification thresholds are therefore set at reproducing A3CG's reference level, and the primary acceptance criterion is the evidence-conditioning Δ.** Pick **one** classification definition below and state it in the report; since we evaluate on our own SGX set, A3CG numbers are a reference, not a like-for-like comparison.

| Item | Minimum | Target |
|---|---|---|
| KB | ≥10k chunks and ≥100k words → **≈240 reports at 300-word chunks** (measured, §2.1) | multiple sectors/years plus a ≤1,200-page visual subset |
| Eval set | `eval.xls` ≥1,000 including no-pair; pair/action IAA ≥0.80 and span agreement reported separately, per the staged protocol in §2.3 | external verification set and qrels ≥50 only after the core set is complete |
| Retrieval | hybrid beats BM25 and dense separately on nDCG@10; company/year filtering lowers wrong-company@10 | visual fusion improves the capped table/chart subset |
| **Classification — option (a), matches the staged annotation protocol**: action classification **given a gold aspect span** (3-way), accuracy reported alongside | macro-F1 at A3CG's T5-baseline AC level: ≥ 0.55 (seen), ≥ 0.25 (unseen) | A3CG's best published AC: ≥ 0.60 / ≥ 0.36 |
| **Classification — option (b)**: A3CG's joint **AAA F1**, directly comparable to the literature | ≥ 0.60 (seen), ≥ 0.40 (unseen) | ≥ 0.68 / ≥ 0.47 (i.e. approaching COGLM's 67.6 / 49.0) |
| **Evidence-conditioning ablation** (headline, primary acceptance item) | ΔF1 of each evidence condition over sentence-only plus flip analysis, with a McNemar test or bootstrap 95 % CI; seen/unseen separately; retrieval metrics reported alongside. A negative result is still a valid result | Δ significantly positive on the ellipsis / unattributed buckets and not significant on negation / modality (as predicted) |
| Cross-year trajectories / verification | ~60 (company, aspect) × ≥3-year trajectory set with trajectory exact-match and transition F1 | optional external supports/refutes/NEI macro-F1 ≥0.55 |
| Generation | RAGAS faithfulness ≥ 0.75; every risk hint traceable to a page; citation precision on 50 manually checked answers reported separately | ≥ 0.85 |
| Performance | end-to-end ≤ 8 s (visual retrieval is heavier; measure visual reranking separately) | ≤ 4 s |
| UI | company + claim input, evidence page thumbnails, 5 timed queries | — |

---

## 6. Citation audit and paper roles ([OneDrive paper folder](Useful%20Paper.html))

| Verified source | Use and boundary |
|---|---|
| [A3CG](https://aclanthology.org/2025.acl-long.723/) (ACL 2025) | **Core basis** for pair/no-pair, aspect spans, actions and seen/unseen evaluation. It explicitly does not perform definitive greenwashing detection. Note it reports **no IAA figure**. |
| [COGLM / Robust greenwashing LM](https://arxiv.org/abs/2601.21722) (preprint, Jan 2026) | **The same group's direct follow-up to A3CG and the current SOTA (72.4 / 67.6 / 49.0).** A baseline to reproduce and beat with retrieval — *not* available novelty. |
| **[EmeraldMind](https://arxiv.org/abs/2512.11506) (ACM Web Conference 2026) + EmeraldApp demo** | **The closest existing system: KG + vector RAG for greenwashing detection with evidence-backed justification and abstention.** Must be cited and differentiated (§1.4). Its weaknesses — 37 reports, semi-synthetic LLM-generated/labelled claims, no aspect–action granularity, no temporal dimension, no SGX — are our differentiators. |
| [ML-Promise](https://aclanthology.org/2025.emnlp-main.1028/) (EMNLP 2025) | **Direct precedent for report-internal evidence checking** (PI / AE / CPEP / TV, evidence within the same document, RAG + image baselines, κ 0.60–0.96). Prioritise it in related work over generic AVeriTeC. |
| [Corporate greenwashing survey](https://arxiv.org/abs/2502.07541) (Calamai et al., v2 Jan 2026) | Definitions, data and methods; its finding that **no verified greenwashing dataset exists** and its recommendation of **decomposed, human-oversight pipelines** are the strongest support for our risk-screening framing. |
| [SwissText 2025 ESG hints](https://aclanthology.org/2025.swisstext-1.3/) | Proceedings paper over 150 German DAX reports; **already establishes** specificity + internal-substantiation risk hints, with a domain gap to SGX. Cite as prior art, not as our idea. |
| [ClimateBERT environmental claims](https://arxiv.org/abs/2209.00507) | Environmental-claim data and baseline for candidate-sentence filtering. Add `climate_specificity` for the vagueness signal. All climatebert sets are CC-BY-NC-SA-4.0. |
| [ESGBench](https://arxiv.org/abs/2511.16438) (ICAIF 2025 workshop) | Small (12 reports / 119 QA) but useful evidence for how hard numeric and table grounding in ESG PDFs is (EM 21 %, numeric 45 %). Sets realistic generation expectations. |
| [ViDoRe V3](https://arxiv.org/abs/2601.08620) / [ColPali](https://arxiv.org/abs/2407.01449) | Visual-page retrieval basis; label ViDoRe V3 as a preprint rather than “ACL 2026”. |
| [Qwen3-VL Embedding](https://arxiv.org/abs/2601.04720) / [UniDoc-Bench](https://arxiv.org/abs/2510.03663) (preprints) | Visual embedding/reranking and multimodal evaluation candidates; do not promise to implement every model. All four arXiv IDs in this row and the one above were re-verified 2026-09-10. |
| [AVeriTeC 2025 overview](https://aclanthology.org/2025.fever-1.15/) / [winner system](https://aclanthology.org/2025.fever-1.22/) | Optional external-fact-checking pipeline. The old `2024_AIC-CTU` PDF is a 2024 predecessor, not the 2025 winner paper. |
| [Ev2R](https://arxiv.org/abs/2411.05375) | Evidence-recall evaluation; needed only if external verification is implemented. |
| [Shared OneDrive paper folder](../Common%20Useful%20Paper.html) | General RAG, evaluation and chunking background. |

---

## 7. Challenges

1. **Annotation and IAA — the dominant schedule risk.** A3CG used 5 sustainability PhD/postdoc annotators plus 3 verifiers and still reports **no κ**. Our ≥80 % requirement is ours alone to meet; use the staged accept/reject protocol in §2.3 and budget two pilot rounds in weeks 1–2. Expect disagreement to concentrate on `implemented` vs `indeterminate`.
2. **PDF engineering**: complex layouts (two columns, charts, tables across pages) make text extraction noisy — and the ACL-published A3CG text carries the same artifacts, so this is tolerable rather than fatal. Visual retrieval avoids OCR but the index is heavy; the ≤1,200-page cap in §4.2 bounds it to ~0.3 GB.
3. **Corpus crawling is the real KB cost**: ~240 reports means a crawler across ~60–80 company IR sites × 3–4 years, roughly 1–2 person-weeks. There is no verified single bulk source; `sustainabilityreports.com` advertises bulk download by country/year and is worth one hour of piloting because it could remove the crawler entirely.
4. **Sparse external evidence**: many smaller issuers have no stable external coverage, so a verification subset will skew to NEI. The survey confirms no verified greenwashing dataset exists. **Recommendation: cut external fact-checking, or keep it as a stretch goal with no acceptance criterion** — it adds the most work for the least defensible result.
5. **Compute is not the bottleneck**: A3CG's own experiments ran on a *single RTX 4090*. Only the visual index needs real GPU time (~0.3 GB / <1 h at the capped size). Without a GPU, fall back to `vidore/colSmol-500M` or cloud.
6. **Close to the professor and postdoc's group** — and now also close to EmeraldMind (WWW 2026) and ML-Promise (EMNLP 2025). The alignment is useful but invites scrutiny. Separate reused A3CG components from our new retrieval, evidence-conditioning and cross-year components explicitly, and cite all three prior systems.
7. **Legal / reputational**: even a “greenwashing risk signal” is sensitive; the UI and report must continuously state “assistive screening, not a verdict” and avoid classifying specific companies as greenwashers.

---

## 8. Other notes

- **Split**: KB — the whole team together (PDF crawling / parsing, page rendering, metadata, claim extraction); retrieval team 3 (text / visual dual index, fusion, reranking, ablations); downstream team 2 (classifier, evidence-conditioning ablation, explanation generation, RAGAS, UI).
- **Timeline** (deadline 2026-11-07): **W1 the KB pair starts crawling immediately** — do not wait until W3. W1–2 run licensing/download/parsing/size pilots over ~30 companies × 3 years (~90 reports) plus annotation pilots, and reproduce GRACE + a T5-base baseline; W3–4 scale to the ~240-report threshold and finish the text v0 + UI; W5–7 add metadata/cross-year retrieval, the evidence-conditioning ablation and classification, then visual retrieval if resources permit; W8–9 evaluation; W10 report.
- **Week-1 checklist**:
  1. Run GRACE fold-1 seen/unseen from `keanepotato/a3cg_greenwash` with the HF checkpoint; confirm ≈60.87 seen / 50.08 unseen. If it reproduces, the whole downstream half de-risks in a day.
  2. Fine-tune one T5-base on `full_train.json`; target ≈70.5 full-dataset AAA F1 as our internal baseline.
  3. Pilot ~90 reports end-to-end (download → parse → chunk → count); report parse-failure rate and re-extrapolate the 240-report target.
  4. Pilot `sustainabilityreports.com` bulk download for one hour.
  5. Annotation pilot round 1: 50 statements, 3 annotators, staged protocol, per-dimension agreement.
  6. Decide the classification metric (§5) before anything else is built.
- **Follow-on research**: if release rights, rigorous results and a systematic novelty search support it, discuss follow-on work with the professor and postdoc's group. The course proposal should not promise collaboration, Q1/Q2 publication or a “first system”.
- **Fallback**: if visual retrieval is compute-bound, drop to text + structured table extraction — still satisfies the assignment.

---

## 9. Links

- **A3CG code + data (use this one)**: https://github.com/keanepotato/a3cg_greenwash ; checkpoints: https://huggingface.co/keentomato (`a3cg_greenwash_grace_f1/f2/f3`) ; mirror without code: https://github.com/SenticNet/greenwashing-detection ; paper page: https://aclanthology.org/2025.acl-long.723/
- EmeraldMind (WWW 2026): https://arxiv.org/abs/2512.11506 ; ML-Promise data: http://MLpromise.nlpfin.com/
- ClimateBERT datasets: https://huggingface.co/climatebert
- ViDoRe / ColPali models: https://huggingface.co/vidore ; Qwen3-VL-Embedding: https://huggingface.co/Qwen
- **SGXNet direct PDF pattern**: `https://links.sgx.com/1.0.0/corporate-announcements/<ANNOUNCEMENT_ID>/<file>.pdf` (no auth; `api.sgx.com/announcements/...` requires auth)
- SustainabilityReports.com: https://www.sustainabilityreports.com/ ; SGX sustainability-reporting rules: https://www.sgx.com/regulation/sustainability-reporting
- NUS CGS × SGX Sustainability Reporting Review 2023: https://bschool.nus.edu.sg/cgs/wp-content/uploads/sites/7/2023/11/CGS-SGX-Sustainability-Reporting-Review-2023_Report.pdf
- AVeriTeC 2025 winner code: https://github.com/aic-factcheck/aic_averitec ; HerO: https://github.com/ssu-humane/HerO
- Tooling: pymupdf / marker, pdfplumber, Pyserini, FAISS / Qdrant, colpali-engine, ir_measures, RAGAS, vLLM, Gradio
