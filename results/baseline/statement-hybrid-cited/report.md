# 20261029T143225Z-baseline-rag-rq1

- system: `baseline-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `b3d06731` (dirty) · wall: 2943.8s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7451 ±0.019 | 0.7707 ±0.015 | 0.7689 ±0.015 | 0.7397 | 39 | — | — | — | 8638.1 | 993 |
| local | 0.7453 ±0.007 | 0.7791 ±0.003 | 0.7786 ±0.004 | 0.7617 | 36 | +0.0001 | +38/-44 | 0.824 | 4750.3 | 993 |
| same_report_rrf | 0.7380 ±0.006 | 0.7693 ±0.005 | 0.7689 ±0.006 | 0.7442 | 44 | -0.0072 | +40/-56 | 0.678 | 6659.7 | 993 |
| cross_year_rrf | 0.7676 ±0.004 | 0.7893 ±0.005 | 0.7883 ±0.006 | 0.7767 | 36 | +0.0225 | +41/-34 | 0.210 | 4762.2 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 2.00 | 331 | {'rrf+rerank': 662} |
| cross_year_rrf | 0.89 | 2.66 | 0 | {'rrf+rerank': 879} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 2766 / 5766 | 2766 / 5766 | 2.51 | 540 / 89 | 0.215 | 0 |
| local | — / — | 2751 / 4585 | 2751 / 4585 | 2.61 | 656 / 100 | 0.251 | 0 |
| same_report_rrf | 734 / 1449 | 2938 / 5264 | 3805 / 6213 | 2.29 | 665 / 105 | 0.259 | 0 |
| cross_year_rrf | 191 / 954 | 2910 / 6399 | 3214 / 6686 | 2.39 | 692 / 97 | 0.255 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 17.8 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 18.9 | 1.000 | 1.07 | — | — | 0.0 |
| same_report_rrf | 1.000 | 1.000 | 19.0 | 1.000 | 1.10 | 0.091 | 0.048 | 0.0 |
| cross_year_rrf | 1.000 | 1.000 | 18.6 | 1.000 | 1.01 | 0.011 | 0.004 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8269 | 0.7972 | 0.5950 | 0.7660 |
| local | 0.8522 | 0.8058 | 0.6271 | 0.7045 |
| same_report_rrf | 0.8385 | 0.8028 | 0.5913 | 0.6897 |
| cross_year_rrf | 0.8421 | 0.8321 | 0.6560 | 0.7391 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7379 | 0.6825 | 0.7928 |
| local | 0.7611 | 0.7051 | 0.8157 |
| same_report_rrf | 0.7425 | 0.6866 | 0.7944 |
| cross_year_rrf | 0.7748 | 0.7210 | 0.8277 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7443 | 0.3162 |
| local | 0.7678 | 0.3162 |
| same_report_rrf | 0.7486 | 0.3162 |
| cross_year_rrf | 0.7840 | 0.3162 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3162 | 0.7443 | n/a |
| local | 0.3162 | 0.7678 | n/a |
| same_report_rrf | 0.3162 | 0.7486 | n/a |
| cross_year_rrf | 0.3162 | 0.7840 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.4141 | 0.7575 |
| local | 0.4165 | 0.7806 |
| same_report_rrf | 0.2929 | 0.7676 |
| cross_year_rrf | 0.3111 | 0.8013 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.5833 | 0.9030 | 0.7180 | 0.7616 | 0.5628 | 0.7190 | 0.7145 | 0.9441 | 0.6946 | 0.7959 |
| local | n/a | 0.8308 | 0.9030 | 0.9030 | 0.7392 | 0.5990 | 0.7725 | 0.7525 | 0.9008 | 0.6933 | 0.7451 |
| same_report_rrf | n/a | 0.8308 | 0.7364 | 0.7894 | 0.7608 | 0.6194 | 0.7886 | 0.7265 | 0.9441 | 0.6933 | 0.6105 |
| cross_year_rrf | n/a | 0.7596 | 1.0000 | 0.7894 | 0.7608 | 0.6194 | 0.8796 | 0.7561 | 0.9043 | 0.7194 | 0.7959 |
