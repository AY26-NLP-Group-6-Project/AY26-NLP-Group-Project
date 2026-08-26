# Proposal 3 · Greenwash-RAG: Greenwashing-Risk-Aware Evidence RAG over SGX Sustainability Reports

> Recommendation: 🥉 highest ceiling / highest risk (directly aligned with the ACL 2025 work of the professor and postdoc's group) ｜ 中文版：[README_CN.md](README_CN.md) ｜ [OneDrive paper folder](Useful%20Paper.html)
> One-liner: given a company plus a sustainability claim or aspect, the system retrieves report-internal evidence, extracts aspect–action relations and distinguishes **implemented / planning / indeterminate**. Visual pages and external evidence are enhancements. The output is evidence-backed risk screening, not a definitive verdict that a company is greenwashing.

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

- [A3CG](https://aclanthology.org/2025.acl-long.723/), an ACL 2025 paper from the professor and postdoc's group, provides the aspect–action scheme, data and seen/unseen protocol. Extending sentence analysis to report-internal evidence retrieval and cross-year comparison is natural. Our quick search found no exactly equivalent system, but “nobody has built this” requires a systematic novelty review.
- SGX sustainability and climate-disclosure rules provide locally relevant longitudinal documents. Since the rules evolve, cite the [current SGX Rulebook](https://rulebook.sgx.com/rulebook/711b) and [reporting guide](https://rulebook.sgx.com/rulebook/practice-note-7f-sustainability-reporting-guide), not only a static 2016/2022 summary. Table/chart pages can support a controlled visual-retrieval enhancement.
- Hits both the "climate resilience (greenwashing detection)" and "finance" lines on the SenticNet project page.

### 1.3 Mapping to the grading rubric

| Rubric item | This project |
|---|---|
| KB (20) | PDF crawling / parsing (text + page images), section / page chunking, company / year metadata, `eval.xls` |
| Retrieval (40) | MVP: text hybrid retrieval + company/year filters + reranking; enhancement: visual retrieval/fusion on a controlled table/chart subset |
| Downstream (40) | MVP: A3CG-style pair/no-pair, aspect span, action classification and evidence explanation; external fact-checking only if annotation capacity permits |

---

## 2. Data and knowledge base

### 2.1 Sources

| Source | Access | Use | Notes |
|---|---|---|---|
| SGX-listed sustainability reports | company IR pages and SGXNet; third-party indexes for discovery only | `KB_report` | public visibility does not automatically permit bulk redistribution; save source URL/date, robots/terms and report copyright, and release only permitted derivatives |
| A3CG dataset | [greenwashing-detection repo](https://github.com/SenticNet/greenwashing-detection) (`dataset/full`, 3 folds) | train/compare the aspect–action classifier | data is accessible; at validation time parts of code/model evaluation were still marked “coming soon”, so do not claim turnkey reproduction |
| ClimateBERT data | [climatebert/environmental_claims](https://huggingface.co/datasets/climatebert/environmental_claims), `climate_detection`, `tcfd_recommendations` | claim-detection candidates | check each data card, licence, label definition and domain gap |
| External news / regulation | Eco-Business, CNA, SGX RegCo, MAS, NEA public pages | optional `KB_external` | check each site's crawl/reuse terms; paywalled or unstable content is not part of the core KB |
| Kaggle S&P 500 ESG reports | [S&P 500 ESG reports](https://www.kaggle.com/datasets/jaidityachopra/esg-sustainability-reports-of-s-and-p-500-companies) | extra training / background | optional |

**Size must be measured.** The old “~600 issuers × five years, 60 pages each” estimate combined unsnapshotted assumptions and is removed. In week 1, sample 20–30 companies across sectors and 2–3 years, then report download/parse success, pages, text chunks and words before extrapolating the minimum corpus needed for 10k chunks/100k words. Visually index a controlled, naturally occurring table/chart subset rather than every page by default.

### 2.2 Parsing and chunking

- Text: `pymupdf` / `marker` extraction + tables via `camelot` / `pdfplumber`; 200–400-word chunks by heading hierarchy with a "company | year | section" contextual header.
- Visual: render each page at 150 dpi; encode with ColQwen2.5 / Qwen3-VL-Embedding; dual index (page level + text-chunk level); when fusing, expand a page hit into its chunks.
- Metadata: `{company, ticker, sector, year, page, section, has_table, has_chart}`.

### 2.3 Evaluation set (≥ 1,000 rows, IAA ≥ 80 %)

- **`eval.xls`**: ≥1,000 SGX-report sentences including environmental claims and controls. Label `has_aspect_action` and `aspect_span`; assign `action ∈ {implemented, planning, indeterminate}` only when a pair exists. `specificity` is optional. About **33.2% of A3CG statements contain no aspect–action pair**, so retain a no-pair class instead of balancing only the three actions.
  - The A3CG guideline is a starting point, not an IAA guarantee. Independently double-code 100 items; report raw agreement plus κ/α for pair/action and token-level F1/overlap agreement for spans before adjudication.
- **External verification set (optional)**: add claim + evidence + `supports/refutes/NEI` only after the core 1,000 items are complete and evidence is reliably available. Do not select only large companies to guarantee refutations and then claim population-level performance.
- **Retrieval qrels**: start with ≥50 queries × pooled top-10. Report the naturally occurring table/chart subset separately rather than forcing one-third of answers to be visual.

---

## 3. Baseline level

| Layer | Current level | Source |
|---|---|---|
| Aspect–action classification | A3CG covers 1,679 SGX reports and 2,004 statements and shows a seen-to-unseen degradation; it explicitly is not definitive greenwashing detection | [A3CG, ACL 2025](https://aclanthology.org/2025.acl-long.723/) |
| Greenwashing-risk robustness | Contrastive, ordinal and gated objectives are candidates for cross-category robustness; treat the work as a preprint | [Robust greenwashing LM](https://arxiv.org/abs/2601.21722) |
| Environmental-claim detection | Expert-annotated binary environmental-claim data plus a ClimateBERT baseline; the unsourced “F1≈0.8+” shorthand is removed | [ClimateBERT environmental claims](https://arxiv.org/abs/2209.00507) |
| Visual document retrieval | Supports separate visual/text/hybrid retrieval and generation evaluation; its public record does not establish “ACL 2026 accepted” | [ViDoRe V3, preprint](https://arxiv.org/abs/2601.08620) |
| RAG fact-checking | Cite the 2025 overview/winner paper for the winning system and efficiency; the 2024 AIC-CTU paper is a predecessor, not the 2025 winner paper | [overview](https://aclanthology.org/2025.fever-1.15/), [winner paper](https://aclanthology.org/2025.fever-1.22/), [2024 predecessor](https://arxiv.org/abs/2410.11446) |
| Internal v0 | text BM25 + bge dense + RRF + reranker; classifier = DeBERTa fine-tuned on A3CG; verification = LLM + top-5 external evidence | this project |

---

## 4. Method

### 4.1 Architecture

```
(company, claim / aspect, year?) ─► query construction (company aliases, aspect synonyms)
   ─► text hybrid retrieval (BM25 + bge-m3 + RRF) ─┐
   ─► optional visual page retrieval (ColQwen / Qwen3-VL-Emb) ┴► cross-modal fusion ─► rerank
   ─► evidence: report passages + optional page screenshots / external articles
   ─► classification: aspect–action (A3CG fine-tuned model / LLM + RAG)
   ─► optional external verification: NLI / LLM → supports / refutes / NEI
   ─► greenwashing-risk explanation (page citations; vague wording highlighted; target / year / number checks)
   ─► UI: company picker + claim input + evidence page thumbnails + risk cards
```

### 4.2 Retrieval innovations (Q3)

1. Hybrid retrieval + cross-encoder reranking (course requirement).
2. **Visual page retrieval (enhancement)**: fuse only on a natural table/chart subset; ablate text-only/visual-only/fused without making a full-page visual index the minimum deliverable.
3. **Company / year metadata filtering + cross-year comparison retrieval** ("was the 2022 target quietly changed in 2024?" → timeline retrieval).
4. **Query expansion**: aspect synonym table (A3CG aspect categories) + HyDE hypothetical passages.
5. Contextual chunk headers vs. late chunking.

### 4.3 Downstream innovations (Q5)

1. **RAG-augmented aspect–action classification**: the company's earlier claims plus report-internal evidence as context, versus plain sentence classification (A3CG baseline).
2. **Report-internal evidence checking**: retrieve and compare the same company's claims across years first; external AVeriTeC-style verification is a second-stage option.
3. **Greenwashing-risk-signal explanation**: rules (no number/year, vague wording) plus cited LLM explanation; always call it a risk signal and never issue a company-level verdict.
4. **Cross-category generalisation experiment**: reuse A3CG's seen/unseen aspect split and test whether RAG context improves unseen generalisation. It is a useful course experiment, not a promised publication result.
5. Optional: SenticNet concept-level features as a symbolic signal (aligned with tools used by the professor and postdoc's group).

### 4.4 Evaluation

- Retrieval: P@k, R@k, MRR, nDCG@10; table / chart-page subset reported separately.
- Classification: macro P / R / F1 for aspect / action; seen vs. unseen.
- Verification: 3-way macro-F1; Ev2R-style evidence recall (LLM-judged).
- Generation: RAGAS faithfulness / answer relevance / context precision; human Likert.
- System: latency, indexing cost (visual index GPU memory / disk), scalability.

---

## 5. Acceptance criteria (loose for now)

| Item | Minimum | Target |
|---|---|---|
| KB | ≥10k chunks and ≥100k words; report count determined by measured page/parse rates | multiple sectors/years plus a controlled visual-page subset |
| Eval set | `eval.xls` ≥1,000 including no-pair; pair/action IAA ≥0.80 and span agreement reported separately | external verification set and qrels ≥50 only after the core set is complete |
| Retrieval | hybrid beats BM25 and dense separately; company/year filtering has a positive ablation | visual fusion improves the natural table/chart subset |
| Classification | action macro-F1 ≥ 0.70 (seen), ≥ 0.55 (unseen) | ≥ 0.78 / ≥ 0.65 |
| Verification | reproducible metric on report-internal cross-year consistency | optional external supports/refutes/NEI macro-F1 ≥0.55 |
| Generation | RAGAS faithfulness ≥ 0.75; every risk hint traceable to a page | ≥ 0.85 |
| Performance | end-to-end ≤ 8 s (visual retrieval is heavier) | ≤ 4 s |
| UI | company + claim input, evidence page thumbnails, 5 timed queries | — |

---

## 6. Citation audit and paper roles ([OneDrive paper folder](Useful%20Paper.html))

| Verified source | Use and boundary |
|---|---|
| [A3CG](https://aclanthology.org/2025.acl-long.723/) (ACL 2025) | **Core basis** for pair/no-pair, aspect spans, actions and seen/unseen evaluation. It explicitly does not perform definitive greenwashing detection. |
| [Robust greenwashing LM](https://arxiv.org/abs/2601.21722) (preprint) | Candidate contrastive/ordinal/gated enhancement; do not call it a turnkey strong baseline before reproduction. |
| [Corporate greenwashing survey](https://arxiv.org/abs/2502.07541) (working paper) | Definitions, data and methods; its observation that verified greenwashing-case datasets are lacking supports risk-screening language. |
| [SwissText 2025 ESG hints](https://aclanthology.org/2025.swisstext-1.3/) | Proceedings paper over 150 German DAX reports; supports linguistic-specificity/internal-evidence risk hints, with a domain gap to SGX. |
| [ClimateBERT environmental claims](https://arxiv.org/abs/2209.00507) | Environmental-claim data and baseline for candidate-sentence filtering. |
| [ML-Promise](https://aclanthology.org/2025.emnlp-main.1028/) (EMNLP 2025) | More directly relevant to ESG promise verification than generic AVeriTeC; add it to OneDrive and prioritise it in related work. |
| [ViDoRe V3](https://arxiv.org/abs/2601.08620) / [ColPali](https://arxiv.org/abs/2407.01449) | Visual-page retrieval basis; label ViDoRe V3 as a preprint rather than “ACL 2026”. |
| [Qwen3-VL Embedding](https://arxiv.org/abs/2601.04720) / [UniDoc-Bench](https://arxiv.org/abs/2510.03663) (preprints) | Visual embedding/reranking and multimodal evaluation candidates; do not promise to implement every model. |
| [AVeriTeC 2025 overview](https://aclanthology.org/2025.fever-1.15/) / [winner system](https://aclanthology.org/2025.fever-1.22/) | Optional external-fact-checking pipeline. The old `2024_AIC-CTU` PDF is a 2024 predecessor, not the 2025 winner paper. |
| [Ev2R](https://arxiv.org/abs/2411.05375) | Evidence-recall evaluation; needed only if external verification is implemented. |
| [Shared OneDrive paper folder](../Common%20Useful%20Paper.html) | General RAG, evaluation and chunking background. |

---

## 7. Challenges

1. **Hardest annotation of the three**: ESG terminology and the planning / implemented / indeterminate boundary need domain understanding; the A3CG guideline helps, but expect two pilot rounds to reach 80 % IAA.
2. **PDF engineering**: complex layouts (two columns, charts, tables across pages) make text extraction noisy; visual retrieval avoids OCR but the index is heavy (hundreds of vectors per page) — bound the corpus or pool vectors.
3. **Sparse external evidence**: many smaller issuers have no stable external coverage, so a verification subset will skew to NEI. If built, stratify by evidence availability and publish the sampling rule rather than selecting only large firms to guarantee refutations.
4. **Compute**: encoding ~10 k pages with ColQwen2.5-3B takes GPU hours; generation uses an 8B model; without a GPU fall back to `vidore/colSmol-500M` or cloud.
5. **Close to the professor and postdoc's group**: the alignment is useful but invites scrutiny. Separate reused A3CG components from new retrieval, cross-year comparison and optional visual components.
6. **Legal / reputational**: even a “greenwashing risk signal” is sensitive; the UI and report must continuously state “assistive screening, not a verdict” and avoid classifying specific companies as greenwashers.

---

## 8. Other notes

- **Split**: KB team 2 (PDF crawling / parsing, page rendering, metadata, claim extraction); retrieval team 2 (text / visual dual index, fusion, reranking, ablations); downstream team 2 (classifier, verification, explanation generation, RAGAS, UI).
- **Timeline**: W1–2 run licensing/download/parsing/size and annotation pilots over 20–30 companies; W3–4 scale only enough to meet the KB threshold and finish the text v0 + UI; W5–7 add metadata retrieval, classification and ablations, then visual/external verification if resources permit; W8–9 evaluation; W10 report.
- **Follow-on research**: if release rights, rigorous results and a systematic novelty search support it, discuss follow-on work with the professor and postdoc's group. The course proposal should not promise collaboration, Q1/Q2 publication or a “first system”.
- **Fallback**: if visual retrieval is compute-bound, drop to text + structured table extraction — still satisfies the assignment.

---

## 9. Links

- SenticNet greenwashing repo (A3CG): https://github.com/SenticNet/greenwashing-detection ; paper page: https://aclanthology.org/2025.acl-long.723/
- ClimateBERT datasets: https://huggingface.co/climatebert
- ViDoRe / ColPali models: https://huggingface.co/vidore ; Qwen3-VL-Embedding: https://huggingface.co/Qwen
- SustainabilityReports.com: https://www.sustainabilityreports.com/ ; SGX sustainability-reporting rules: https://www.sgx.com/regulation/sustainability-reporting
- NUS CGS × SGX Sustainability Reporting Review 2023: https://bschool.nus.edu.sg/cgs/wp-content/uploads/sites/7/2023/11/CGS-SGX-Sustainability-Reporting-Review-2023_Report.pdf
- AVeriTeC 2025 winner code: https://github.com/aic-factcheck/aic_averitec ; HerO: https://github.com/ssu-humane/HerO
- Tooling: pymupdf / marker, pdfplumber, Pyserini, FAISS / Qdrant, colpali-engine, ir_measures, RAGAS, vLLM, Gradio
