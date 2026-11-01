# 20261029T143243Z-baseline-rag-rq1

- system: `baseline-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `b3d06731` (dirty) · wall: 2549.8s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7517 ±0.005 | 0.7776 ±0.004 | 0.7762 ±0.004 | 0.7580 | 32 | — | — | — | 8654.8 | 993 |
| local | 0.7469 ±0.013 | 0.7827 ±0.011 | 0.7822 ±0.012 | 0.7509 | 33 | -0.0048 | +32/-41 | 0.664 | 4546.3 | 993 |
| same_report_rrf | 0.7534 ±0.004 | 0.7803 ±0.005 | 0.7798 ±0.006 | 0.7499 | 41 | +0.0017 | +41/-47 | 0.557 | 4477.3 | 993 |
| cross_year_rrf | 0.7399 ±0.021 | 0.7636 ±0.020 | 0.7603 ±0.021 | 0.7396 | 44 | -0.0117 | +37/-58 | 0.230 | 4242.6 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 1.91 | 361 | {'rrf+rerank': 632} |
| cross_year_rrf | 0.89 | 2.66 | 0 | {'rrf+rerank': 879} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 2691 / 5645 | 2691 / 5645 | 2.56 | 540 / 87 | 0.213 | 0 |
| local | — / — | 2726 / 4725 | 2726 / 4725 | 2.69 | 656 / 100 | 0.251 | 0 |
| same_report_rrf | 1306 / 1745 | 3043 / 4967 | 4384 / 6521 | 2.45 | 866 / 95 | 0.288 | 0 |
| cross_year_rrf | 874 / 1068 | 2713 / 4557 | 3526 / 5343 | 2.74 | 989 / 86 | 0.301 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 17.7 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 18.8 | 1.000 | 1.07 | — | — | 0.0 |
| same_report_rrf | 1.000 | 1.000 | 19.7 | 1.000 | 1.06 | 0.059 | 0.033 | 0.0 |
| cross_year_rrf | 1.000 | 1.000 | 20.0 | 1.000 | 1.04 | 0.044 | 0.016 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8351 | 0.8261 | 0.6129 | 0.7391 |
| local | 0.8542 | 0.8143 | 0.5841 | 0.6744 |
| same_report_rrf | 0.8304 | 0.8143 | 0.6050 | 0.7045 |
| cross_year_rrf | 0.8239 | 0.8029 | 0.5920 | 0.7033 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7568 | 0.7040 | 0.8101 |
| local | 0.7489 | 0.6918 | 0.8033 |
| same_report_rrf | 0.7475 | 0.6912 | 0.8022 |
| cross_year_rrf | 0.7381 | 0.6837 | 0.7925 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7687 | 0.2619 |
| local | 0.7551 | 0.3162 |
| same_report_rrf | 0.7550 | 0.3162 |
| cross_year_rrf | 0.7484 | 0.2778 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.2619 | 0.7687 | n/a |
| local | 0.3162 | 0.7551 | n/a |
| same_report_rrf | 0.3162 | 0.7550 | n/a |
| cross_year_rrf | 0.2778 | 0.7484 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.4165 | 0.7767 |
| local | 0.3111 | 0.7746 |
| same_report_rrf | 0.3111 | 0.7733 |
| cross_year_rrf | 0.2929 | 0.7626 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.8308 | 0.9030 | 0.7894 | 0.7616 | 0.5803 | 0.7725 | 0.7597 | 0.9441 | 0.6946 | 0.7384 |
| local | n/a | 0.8308 | 0.9030 | 0.8422 | 0.7656 | 0.5990 | 0.7725 | 0.7368 | 0.8944 | 0.6933 | 0.6794 |
| same_report_rrf | n/a | 0.8308 | 0.9030 | 0.6980 | 0.7576 | 0.5955 | 0.8045 | 0.7384 | 0.8944 | 0.6933 | 0.7959 |
| cross_year_rrf | n/a | 0.7091 | 0.8222 | 0.7429 | 0.7370 | 0.6126 | 0.8677 | 0.7412 | 0.8240 | 0.6946 | 0.7384 |
