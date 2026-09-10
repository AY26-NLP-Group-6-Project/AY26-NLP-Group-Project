# AI6127 Group Project · Topic Proposals Overview

> Validated: 2026-08-26 ｜ Deadline: 2026-11-07 23:59 SGT ｜ Brief: [Group Assignment Intro.pdf](../Group%20Assignment%20Intro.pdf) ｜ 中文：[README_CN.md](README_CN.md)
>
> Paper PDFs are now on OneDrive. Each topic's `Useful Paper.html` opens its folder; [Common Useful Paper.html](Common%20Useful%20Paper.html) opens the shared folder. Independent arXiv, ACL Anthology and official links are retained below for claim verification.

## Verdict and ranking

| Directory | Topic | Current recommendation | Main reason |
|---|---|---|---|
| [Patch Version RAG](Patch%20Version%20RAG/README.md) | Version-aware time-travel QA over game patches | 🥇 **safest primary** | Traceable data and answers, a manually verifiable 1,000-question set, and clean ablations for version filtering/routing; one API/licensing pilot can settle feasibility. |
| [Energy Opinion RAG](Energy%20Opinion%20RAG/README.md) | Opinion RAG for the SEA energy transition | 🥈 **conditional alternative** | Excellent course fit, but current Reddit research access requires approval and platform discourse must not be presented as population opinion. |
| [Greenwash RAG](Greenwash%20RAG/README.md) | Evidence-grounded, cross-year tracking of SGX sustainability claims | 🥉 **high ceiling / high risk** | Strong A3CG/local fit and the data is verified available, but the annotation load is highest and the original MVP framing is already occupied by EmeraldMind (WWW 2026) and ML-Promise (EMNLP 2025) — viable only with the evidence-conditioning and cross-year reframing in its README §0 and §1.4. Must assist risk screening rather than issue definitive greenwashing verdicts. |

## Hard constraints from the brief

- KB ≥ 10,000 documents/passages and ≥ 100,000 words; clean, chunk and report document/chunk/word/type statistics yourselves.
- Sparse, dense and hybrid retrieval are mandatory (reranking may be added); no SQL `LIKE`; include a simple UI, five example queries and timing.
- A held-out, self-built evaluation set needs ≥ 1,000 **manually labelled or verified** records, de-duplication, reasonable balance and IAA ≥ 80%; classification tasks submit `eval.xls`. Semi-automatic generation does not remove item-level human verification or an independently double-coded subset.
- Report P@K, R@K, MRR and nDCG for retrieval; report task metrics plus answer-level faithfulness, answer relevance, context relevance/precision (e.g. RAGAS) and performance.
- Each innovation needs a corresponding ablation; >30% overlap with a past or current project receives zero.
- Submit one PDF named with the group number and include OneDrive/Dropbox links for data and code. The HTML redirect files in this repo are literature gateways, not the final data/code submission.

## Feasibility comparison

| Dimension | Patch-Version | Energy-Opinion | Greenwash |
|---|---|---|---|
| Course fit | high: QA + version-metadata retrieval + generation | very high: opinion/sentiment directly matches course interests | very high: extends A3CG and ESG work |
| Data risk | **low–medium**: pilot the Wiki API, reuse terms and Data Dragon coverage | **medium–high**: Reddit for Researchers approval, ethics and no-redistribution conditions | **medium**: many public PDFs, but licences, crawl terms and cut-off snapshots must be recorded |
| 1,000-item evaluation | easiest: verify four QA types item by item and double-code a subset for IAA | medium–hard: too many simultaneous labels will depress IAA | hardest: aspect spans, actions and a no-aspect class require domain judgement |
| Minimum viable innovation | version metadata filtering/routing + stale-evidence warnings | perspective-coverage reranking + one downstream innovation | evidence-conditioned aspect–action ablation (none / local / same-report / cross-year) + cross-year retrieval; visual retrieval only on a capped ≤1,200-page ablation subset |
| Main scope trap | full graph plus complete historical snapshot replay from day one | conditional stance, frames, sarcasm, conflict and Singlish all at once | visual indexing, external fact-checking and company-level verdicts all at once |
| Recommended control | make graph retrieval an enhancement after a strong metadata baseline | obtain data approval or switch to lawfully reusable open opinion data; report sampled platform discourse only | call it a risk-aware assistant; keep report-internal evidence/action classification as the MVP |

## Citation audit

- The core references have public records, but several 2025–2026 works are currently arXiv preprints. The proposals no longer present them as peer-reviewed or conference-accepted without evidence.
- [VersionRAG](https://arxiv.org/abs/2510.08109) supports the 100-question/34-document benchmark and main baselines. [TG-RAG](https://arxiv.org/abs/2510.13590) and [ChronoQA](https://arxiv.org/abs/2508.12282) support the temporal-retrieval motivation, but exact table values should carry page/table citations or be stated qualitatively.
- [O-RAG](https://arxiv.org/abs/2604.12138), [BERDS](https://arxiv.org/abs/2409.18110) and [DIVERGE](https://arxiv.org/abs/2602.00238) support opinion synthesis and perspective coverage; they do not establish that Reddit users represent a national population.
- [A3CG](https://aclanthology.org/2025.acl-long.723/) is Greenwash's strongest basis, but explicitly says it is **not** a definitive greenwashing-detection system, and it reports **no inter-annotator agreement figure at all**. Updated 2026-09-10: the repo to use is [keanepotato/a3cg_greenwash](https://github.com/keanepotato/a3cg_greenwash) (the one cited in the paper), which ships the dataset **plus** the GRACE implementation, eval scripts and prediction dumps, with checkpoints on HF under `keentomato`; the `SenticNet` mirror's "code coming soon" note is stale. Neither repo has a LICENSE file, and the company/year list promised in the paper's footnote 2 is absent.
- Greenwash's original "no exactly equivalent system" claim is **withdrawn**: [EmeraldMind](https://arxiv.org/abs/2512.11506) (ACM Web Conference 2026) is a KG+vector RAG greenwashing detector with evidence-backed justifications and abstention, and [ML-Promise](https://aclanthology.org/2025.emnlp-main.1028/) (EMNLP 2025) already does report-internal evidence linking for ESG promises. Both must be cited; see [Greenwash README §1.4](Greenwash%20RAG/README.md) for what remains open.
- [ViDoRe V3](https://arxiv.org/abs/2601.08620) supports visual-document retrieval, but its public record does not establish “ACL 2026 accepted”; it is now labelled a preprint.
- The AVeriTeC 2025 winner should cite the [official shared-task overview](https://aclanthology.org/2025.fever-1.15/) and [winning system paper](https://aclanthology.org/2025.fever-1.22/). The previously listed 2024 AIC-CTU paper is a predecessor, not the 2025 winner paper.

## Online paper folders

| Folder | Contents |
|---|---|
| [Common Useful Paper](Common%20Useful%20Paper.html) | General RAG, Agentic RAG, evaluation, LiveRAG, chunking, graphs and conflicts |
| [Energy Useful Paper](Energy%20Opinion%20RAG/Useful%20Paper.html) | Opinion RAG, perspective retrieval, Reddit/Singlish and nuclear discourse |
| [Patch Useful Paper](Patch%20Version%20RAG/Useful%20Paper.html) | VersionRAG, TG-RAG, ChronoQA, temporal robustness and conflict handling |
| [Greenwash Useful Paper](Greenwash%20RAG/Useful%20Paper.html) | A3CG, environmental claims, visual-document retrieval and AVeriTeC |

All four HTML meta-refresh files resolve to the intended SharePoint folders, but please login with an MS account; otherwise automated requests return HTTP 403 (NTU enforced authentication).

## Suggested decision process

1. Default to Patch-Version. In week 1, pilot 100 pages/patches, record licence terms, extrapolate the 10k-chunk count, and independently double-code 50 questions before scaling.
2. If choosing Energy, first obtain [Reddit for Researchers](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program) approval plus institutional ethics approval/exemption; otherwise switch to a reusable open opinion corpus.
3. Choose Greenwash only if the team has ESG annotation and PDF-processing capacity **and accepts the evidence-conditioning reframing** — the original framing is occupied by published work. Data risk is now measured rather than assumed: A3CG plus GRACE code and checkpoints are in hand, and an SGX PDF pilot gives ~12.6k words / 43.8 pages per report, so ≈240 reports are needed for the 10k-chunk floor. Build the text MVP first; add visual-page retrieval in a capped ablation, and treat external verification as a stretch goal with no acceptance criterion.
4. After selection, replace `<Pending Proposal>` in the repository root README and document overlap checking, the data cut-off, licensing and ethics in the report.

## Validation boundary

This audit checked the brief, bibliographic metadata, key claims in abstracts/full text, and the main data entry points. It is not a reproduction of every experiment. Any retained exact number should receive a page or table citation in the final report.
