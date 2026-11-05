# 20261105T142254Z-agentic-rag-rq1

> **Test split.** Open it once, for the final report; tune on `dev`.

- system: `agentic-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 669 · labels: `human_majority` · split: `test` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `0f900991` · wall: 5827.9s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7673 ±0.003 | 0.7891 ±0.002 | 0.7884 ±0.003 | 0.7706 | 69 | — | — | — | 8571.3 | 2007 |
| local | 0.7764 ±0.008 | 0.7980 ±0.008 | 0.7968 ±0.008 | 0.7858 | 66 | +0.0091 | +76/-139 | 0.025 | 5095.9 | 2007 |
| same_report_rrf | 0.7625 ±0.005 | 0.7861 ±0.004 | 0.7842 ±0.004 | 0.7642 | 82 | -0.0048 | +75/-141 | 0.003 | 5124.0 | 2007 |
| cross_year_rrf | 0.7539 ±0.003 | 0.7747 ±0.003 | 0.7740 ±0.003 | 0.7564 | 84 | -0.0134 | +66/-132 | 0.001 | 6296.4 | 2007 |
| cross_year_agentic | 0.7596 ±0.009 | 0.7810 ±0.008 | 0.7794 ±0.008 | 0.7644 | 75 | -0.0077 | +64/-98 | 0.117 | 4545.0 | 2007 |
| company_agentic | 0.7711 ±0.010 | 0.7923 ±0.008 | 0.7914 ±0.008 | 0.7734 | 75 | +0.0038 | +68/-98 | 0.152 | 3944.2 | 2007 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 2.00 | 672 | {'hybrid+rerank': 1335} |
| cross_year_rrf | 0.90 | 2.70 | 0 | {'hybrid+rerank': 1803} |
| cross_year_agentic | 0.08 | 0.12 | 0 | {'agent:hop1': 78} |
| company_agentic | 0.16 | 0.21 | 0 | {'agent:hop1': 143} |

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| cross_year_agentic | 1.20 | 536 / 122 | 1.000 | 0.916 | {'no_gap': 520, 'unresolved': 78, 'resolved': 56, 'nothing_found': 15} |
| company_agentic | 1.23 | 557 / 129 | 1.000 | 0.845 | {'no_gap': 514, 'resolved': 104, 'unresolved': 51} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 2353 / 5421 | 2353 / 5421 | 2.93 | 540 / 86 | 0.211 | 0 |
| local | — / — | 2840 / 8255 | 2840 / 8255 | 2.27 | 657 / 97 | 0.247 | 0 |
| same_report_rrf | 2781 / 13385 | 2919 / 5502 | 6055 / 17233 | 2.45 | 667 / 104 | 0.259 | 0 |
| cross_year_rrf | 1598 / 4535 | 2752 / 4916 | 4601 / 7848 | 2.70 | 697 / 95 | 0.253 | 0 |
| cross_year_agentic | 2895 / 10973 | 2477 / 4849 | 5700 / 14658 | 2.80 | 1082 / 209 | 0.468 | 0 |
| company_agentic | 2320 / 9101 | 2389 / 4118 | 4851 / 12116 | 3.07 | 1110 / 218 | 0.484 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 18.0 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 19.1 | 1.000 | 1.06 | — | — | 0.0 |
| same_report_rrf | 1.000 | 1.000 | 19.4 | 1.000 | 1.08 | 0.077 | 0.041 | 0.0 |
| cross_year_rrf | 1.000 | 1.000 | 19.1 | 1.000 | 1.02 | 0.019 | 0.007 | 0.0 |
| cross_year_agentic | 1.000 | 1.000 | 18.0 | 1.000 | 1.01 | 0.119 | 0.085 | 0.0 |
| company_agentic | 1.000 | 1.000 | 18.2 | 1.000 | 1.03 | 0.176 | 0.138 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8434 | 0.7810 | 0.6875 | 0.8426 |
| local | 0.8562 | 0.7881 | 0.7132 | 0.6588 |
| same_report_rrf | 0.8428 | 0.7754 | 0.6745 | 0.6932 |
| cross_year_rrf | 0.8296 | 0.7574 | 0.6822 | 0.7333 |
| cross_year_agentic | 0.8377 | 0.7786 | 0.6770 | 0.7958 |
| company_agentic | 0.8488 | 0.7839 | 0.6875 | 0.7609 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7697 | 0.7309 | 0.8072 |
| local | 0.7853 | 0.7474 | 0.8238 |
| same_report_rrf | 0.7632 | 0.7243 | 0.8012 |
| cross_year_rrf | 0.7555 | 0.7166 | 0.7954 |
| cross_year_agentic | 0.7640 | 0.7257 | 0.8032 |
| company_agentic | 0.7727 | 0.7352 | 0.8093 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=537) | no_aspect (n=132) |
|---|---|---|
| sentence_only | 0.7725 | 0.6859 |
| local | 0.7909 | 0.6117 |
| same_report_rrf | 0.7700 | 0.5816 |
| cross_year_rrf | 0.7621 | 0.5816 |
| cross_year_agentic | 0.7695 | 0.5665 |
| company_agentic | 0.7774 | 0.6117 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=24) | llm_proposed (n=537) | none_proposed (n=108) |
|---|---|---|---|
| sentence_only | 0.6859 | 0.7725 | n/a |
| local | 0.6117 | 0.7909 | n/a |
| same_report_rrf | 0.5816 | 0.7700 | n/a |
| cross_year_rrf | 0.5816 | 0.7621 | n/a |
| cross_year_agentic | 0.5665 | 0.7695 | n/a |
| company_agentic | 0.6117 | 0.7774 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=1) | unanimous (n=668) |
|---|---|---|
| sentence_only | n/a | 0.7706 |
| local | n/a | 0.7858 |
| same_report_rrf | n/a | 0.7642 |
| cross_year_rrf | n/a | 0.7564 |
| cross_year_agentic | n/a | 0.7644 |
| company_agentic | n/a | 0.7734 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=107) | business compliance (n=42) | data and cybersecurity protection (n=24) | ecological conservation (n=41) | emissions control (n=79) | management (n=116) | outreach (n=36) | resource optimisation (n=53) | waste management (n=48) | worker & consumer safety compliance (n=69) | workplace (n=54) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.7919 | 0.6681 | 0.8300 | 0.6823 | 0.7352 | 0.6785 | 0.8265 | 0.7627 | 0.8425 | 0.8488 |
| local | n/a | 0.8453 | 0.6392 | 0.8031 | 0.6690 | 0.7648 | 0.7411 | 0.9112 | 0.7627 | 0.8159 | 0.8851 |
| same_report_rrf | n/a | 0.7655 | 0.7407 | 0.8101 | 0.6701 | 0.6874 | 0.7870 | 0.8698 | 0.7436 | 0.7995 | 0.8684 |
| cross_year_rrf | n/a | 0.7173 | 0.6111 | 0.8040 | 0.6691 | 0.7684 | 0.7083 | 0.8043 | 0.7058 | 0.8168 | 0.8684 |
| cross_year_agentic | n/a | 0.7465 | 0.6392 | 0.8300 | 0.6853 | 0.7547 | 0.7339 | 0.8421 | 0.7219 | 0.7903 | 0.8462 |
| company_agentic | n/a | 0.7919 | 0.6392 | 0.7453 | 0.6823 | 0.7687 | 0.7339 | 0.8571 | 0.7644 | 0.7928 | 0.8684 |
