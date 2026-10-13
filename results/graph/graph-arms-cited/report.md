# 20261002T053125Z-graph-rag-rq1

- system: `graph-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `f3c2f2fa` · wall: 701.3s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7556 ±0.012 | 0.7727 ±0.013 | 0.7713 ±0.013 | 0.7633 | 42 | — | — | — | 2997.2 | 993 |
| cross_year_graph | 0.7731 ±0.007 | 0.7900 ±0.002 | 0.7895 ±0.002 | 0.7728 | 34 | +0.0175 | +37/-25 | 0.549 | 2527.6 | 993 |
| cross_year_fused | 0.7759 ±0.015 | 0.7956 ±0.011 | 0.7956 ±0.011 | 0.7799 | 39 | +0.0202 | +64/-31 | 0.078 | 3013.4 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| cross_year_graph | 0.40 | 0.83 | 0 | {'graph:gold_span': 2, 'graph:llm': 8, 'graph:string_match': 266} |
| cross_year_fused | 0.89 | 2.66 | 0 | {'bm25': 603, 'graph:gold_span': 2, 'graph:llm': 8, 'graph:string_match': 266} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 1607 / 2656 | 1607 / 2656 | 4.49 | 540 / 63 | 0.183 | 0 |
| cross_year_graph | 9 / 12 | 1659 / 2552 | 1663 / 2561 | 4.45 | 584 / 71 | 0.203 | 0 |
| cross_year_fused | 11 / 80 | 1841 / 2947 | 1870 / 2958 | 4.07 | 672 / 82 | 0.233 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 22.1 | 1.000 | 1.00 | — | — | 0.0 |
| cross_year_graph | 1.000 | 1.000 | 22.3 | 1.000 | 1.01 | 0.013 | 0.006 | 0.0 |
| cross_year_fused | 1.000 | 1.000 | 22.8 | 1.000 | 1.02 | 0.020 | 0.008 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8239 | 0.8261 | 0.6400 | 0.7917 |
| cross_year_graph | 0.8357 | 0.8369 | 0.6457 | 0.8000 |
| cross_year_fused | 0.8403 | 0.8382 | 0.6613 | 0.8485 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7601 | 0.7052 | 0.8127 |
| cross_year_graph | 0.7703 | 0.7148 | 0.8181 |
| cross_year_fused | 0.7776 | 0.7234 | 0.8270 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7648 | 0.3714 |
| cross_year_graph | 0.7746 | 0.3714 |
| cross_year_fused | 0.7823 | 0.3714 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3714 | 0.7648 | n/a |
| cross_year_graph | 0.3714 | 0.7746 | n/a |
| cross_year_fused | 0.3714 | 0.7823 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.2929 | 0.7875 |
| cross_year_graph | 0.3111 | 0.7970 |
| cross_year_fused | 0.2929 | 0.8051 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.7899 | 0.9030 | 0.6752 | 0.7172 | 0.6700 | 0.8677 | 0.8098 | 0.8279 | 0.7213 | 0.7708 |
| cross_year_graph | n/a | 0.7899 | 0.9030 | 0.6590 | 0.7480 | 0.6890 | 0.8796 | 0.8098 | 0.8279 | 0.6933 | 0.8246 |
| cross_year_fused | n/a | 0.8308 | 0.9030 | 0.7429 | 0.7703 | 0.6700 | 0.8677 | 0.7373 | 0.9441 | 0.7028 | 0.7708 |
