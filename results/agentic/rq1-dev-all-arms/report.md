# 20261031T054130Z-agentic-rag-rq1

- system: `agentic-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `320a4f17` · wall: 2081.3s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7561 ±0.015 | 0.7751 ±0.017 | 0.7737 ±0.017 | 0.7686 | 52 | — | — | — | 2994.8 | 993 |
| local | 0.7598 ±0.026 | 0.7871 ±0.022 | 0.7871 ±0.022 | 0.7745 | 42 | +0.0037 | +63/-47 | 0.311 | 3171.8 | 993 |
| same_report_rrf | 0.7544 ±0.002 | 0.7810 ±0.004 | 0.7810 ±0.004 | 0.7528 | 32 | -0.0017 | +59/-46 | 1.000 | 3412.6 | 993 |
| cross_year_rrf | 0.7841 ±0.010 | 0.8041 ±0.008 | 0.8041 ±0.008 | 0.7988 | 41 | +0.0279 | +59/-42 | 0.281 | 3366.1 | 993 |
| cross_year_agentic | 0.7544 ±0.002 | 0.7766 ±0.004 | 0.7737 ±0.004 | 0.7609 | 37 | -0.0018 | +37/-34 | 0.815 | 3070.7 | 993 |
| company_agentic | 0.7624 ±0.011 | 0.7878 ±0.009 | 0.7859 ±0.009 | 0.7645 | 46 | +0.0062 | +49/-37 | 0.648 | 3202.6 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 2.00 | 331 | {'hybrid+rerank': 662} |
| cross_year_rrf | 0.89 | 2.66 | 0 | {'hybrid+rerank': 879} |
| cross_year_agentic | 0.08 | 0.11 | 0 | {'agent:hop1': 38} |
| company_agentic | 0.13 | 0.18 | 0 | {'agent:hop1': 61} |

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| cross_year_agentic | 1.19 | 531 / 115 | 1.000 | 0.918 | {'no_gap': 263, 'unresolved': 35, 'resolved': 27, 'nothing_found': 6} |
| company_agentic | 1.21 | 545 / 119 | 1.000 | 0.867 | {'no_gap': 262, 'resolved': 44, 'unresolved': 25} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 1677 / 2928 | 1677 / 2928 | 4.22 | 540 / 63 | 0.184 | 0 |
| local | — / — | 1872 / 3184 | 1872 / 3184 | 3.28 | 656 / 79 | 0.226 | 0 |
| same_report_rrf | 2170 / 4515 | 2091 / 3452 | 4435 / 7053 | 3.07 | 665 / 93 | 0.245 | 0 |
| cross_year_rrf | 1531 / 4348 | 1992 / 3278 | 3616 / 6761 | 3.76 | 692 / 86 | 0.242 | 0 |
| cross_year_agentic | 1954 / 7312 | 1695 / 2842 | 3795 / 9634 | 4.07 | 1079 / 180 | 0.432 | 0 |
| company_agentic | 1899 / 7399 | 1740 / 3104 | 3770 / 10009 | 4.08 | 1097 / 188 | 0.445 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 21.9 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 22.9 | 1.000 | 1.06 | — | — | 0.0 |
| same_report_rrf | 1.000 | 1.000 | 22.8 | 1.000 | 1.13 | 0.105 | 0.064 | 0.0 |
| cross_year_rrf | 1.000 | 1.000 | 22.8 | 1.000 | 1.01 | 0.013 | 0.005 | 0.0 |
| cross_year_agentic | 1.000 | 1.000 | 21.9 | 1.000 | 1.01 | 0.074 | 0.053 | 0.0 |
| company_agentic | 1.000 | 1.000 | 21.8 | 1.000 | 1.03 | 0.235 | 0.180 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8261 | 0.8392 | 0.6406 | 0.8041 |
| local | 0.8389 | 0.8529 | 0.6316 | 0.8485 |
| same_report_rrf | 0.8374 | 0.8261 | 0.5950 | 0.8367 |
| cross_year_rrf | 0.8601 | 0.8321 | 0.7040 | 0.7872 |
| cross_year_agentic | 0.8211 | 0.8451 | 0.6167 | 0.7917 |
| company_agentic | 0.8410 | 0.7973 | 0.6552 | 0.8283 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7664 | 0.7140 | 0.8155 |
| local | 0.7726 | 0.7154 | 0.8257 |
| same_report_rrf | 0.7509 | 0.6961 | 0.8012 |
| cross_year_rrf | 0.7968 | 0.7427 | 0.8441 |
| cross_year_agentic | 0.7587 | 0.7048 | 0.8101 |
| company_agentic | 0.7617 | 0.7059 | 0.8137 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7702 | 0.3714 |
| local | 0.7862 | 0.2619 |
| same_report_rrf | 0.7576 | 0.3162 |
| cross_year_rrf | 0.8031 | 0.3714 |
| cross_year_agentic | 0.7611 | 0.3714 |
| company_agentic | 0.7662 | 0.3714 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3714 | 0.7702 | n/a |
| local | 0.2619 | 0.7862 | n/a |
| same_report_rrf | 0.3162 | 0.7576 | n/a |
| cross_year_rrf | 0.3714 | 0.8031 | n/a |
| cross_year_agentic | 0.3714 | 0.7611 | n/a |
| company_agentic | 0.3714 | 0.7662 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.4165 | 0.7879 |
| local | 0.3111 | 0.7999 |
| same_report_rrf | 0.3111 | 0.7763 |
| cross_year_rrf | 0.2929 | 0.8246 |
| cross_year_agentic | 0.2929 | 0.7854 |
| company_agentic | 0.2929 | 0.7886 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.8308 | 0.9030 | 0.7253 | 0.7603 | 0.6313 | 0.8301 | 0.8073 | 0.8944 | 0.6680 | 0.7901 |
| local | n/a | 0.7899 | 0.9030 | 0.9030 | 0.7691 | 0.5868 | 0.8796 | 0.7657 | 0.8944 | 0.8328 | 0.7084 |
| same_report_rrf | n/a | 0.7596 | 0.7364 | 0.7180 | 0.7886 | 0.6307 | 0.8045 | 0.7480 | 0.8944 | 0.6680 | 0.7708 |
| cross_year_rrf | n/a | 0.8308 | 1.0000 | 0.7894 | 0.7886 | 0.6563 | 0.8102 | 0.7431 | 0.9441 | 0.8328 | 0.8246 |
| cross_year_agentic | n/a | 0.8308 | 0.9030 | 0.8197 | 0.6957 | 0.6687 | 0.8677 | 0.7504 | 0.8557 | 0.6762 | 0.7708 |
| company_agentic | n/a | 0.7899 | 0.9030 | 0.7821 | 0.7868 | 0.6636 | 0.7190 | 0.8098 | 0.8279 | 0.6686 | 0.7708 |
