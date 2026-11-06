# 20261105T103927Z-graph-rag-rq1

> **Test split.** Open it once, for the final report; tune on `dev`.

- system: `graph-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 669 · labels: `human_majority` · split: `test` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `12d04c7b` (dirty) · wall: 2354.3s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7677 ±0.002 | 0.7891 ±0.004 | 0.7872 ±0.004 | 0.7663 | 74 | — | — | — | 3441.4 | 2007 |
| local | 0.7698 ±0.009 | 0.7920 ±0.008 | 0.7908 ±0.007 | 0.7769 | 86 | +0.0021 | +73/-130 | 0.076 | 3563.3 | 2007 |
| cross_year_graph | 0.7646 ±0.003 | 0.7841 ±0.004 | 0.7830 ±0.004 | 0.7708 | 75 | -0.0032 | +63/-77 | 1.000 | 3573.8 | 2007 |
| cross_year_fused | 0.7549 ±0.008 | 0.7765 ±0.007 | 0.7758 ±0.007 | 0.7582 | 94 | -0.0129 | +67/-117 | 0.072 | 4350.0 | 2007 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| cross_year_graph | 0.42 | 0.84 | 0 | {'graph:gold_span': 5, 'graph:llm': 19, 'graph:string_match': 535} |
| cross_year_fused | 0.90 | 2.70 | 0 | {'bm25': 1244, 'graph:gold_span': 5, 'graph:llm': 19, 'graph:string_match': 535} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 1979 / 3382 | 1979 / 3382 | 3.66 | 540 / 86 | 0.211 | 0 |
| local | — / — | 2104 / 3518 | 2104 / 3518 | 3.53 | 657 / 95 | 0.245 | 0 |
| cross_year_graph | 6 / 8 | 2056 / 3629 | 2061 / 3651 | 3.54 | 585 / 90 | 0.225 | 0 |
| cross_year_fused | 9 / 34 | 2195 / 4905 | 2206 / 4913 | 3.09 | 683 / 93 | 0.248 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 17.8 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 19.1 | 1.000 | 1.06 | — | — | 0.0 |
| cross_year_graph | 1.000 | 1.000 | 18.2 | 1.000 | 1.01 | 0.013 | 0.008 | 0.0 |
| cross_year_fused | 1.000 | 1.000 | 19.1 | 1.000 | 1.01 | 0.016 | 0.005 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8379 | 0.7709 | 0.6902 | 0.8325 |
| local | 0.8497 | 0.7883 | 0.6926 | 0.7006 |
| cross_year_graph | 0.8421 | 0.7581 | 0.7121 | 0.8308 |
| cross_year_fused | 0.8370 | 0.7528 | 0.6848 | 0.7742 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7655 | 0.7274 | 0.8030 |
| local | 0.7761 | 0.7387 | 0.8131 |
| cross_year_graph | 0.7700 | 0.7334 | 0.8069 |
| cross_year_fused | 0.7571 | 0.7183 | 0.7929 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=537) | no_aspect (n=132) |
|---|---|---|
| sentence_only | 0.7702 | 0.6117 |
| local | 0.7811 | 0.6117 |
| cross_year_graph | 0.7754 | 0.6117 |
| cross_year_fused | 0.7617 | 0.6117 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=24) | llm_proposed (n=537) | none_proposed (n=108) |
|---|---|---|---|
| sentence_only | 0.6117 | 0.7702 | n/a |
| local | 0.6117 | 0.7811 | n/a |
| cross_year_graph | 0.6117 | 0.7754 | n/a |
| cross_year_fused | 0.6117 | 0.7617 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=1) | unanimous (n=668) |
|---|---|---|
| sentence_only | n/a | 0.7663 |
| local | n/a | 0.7769 |
| cross_year_graph | n/a | 0.7708 |
| cross_year_fused | n/a | 0.7582 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=107) | business compliance (n=42) | data and cybersecurity protection (n=24) | ecological conservation (n=41) | emissions control (n=79) | management (n=116) | outreach (n=36) | resource optimisation (n=53) | waste management (n=48) | worker & consumer safety compliance (n=69) | workplace (n=54) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.8296 | 0.6610 | 0.8300 | 0.6948 | 0.7576 | 0.6785 | 0.8209 | 0.7038 | 0.8059 | 0.8398 |
| local | n/a | 0.7984 | 0.6026 | 0.7749 | 0.6953 | 0.7533 | 0.7411 | 0.8393 | 0.7644 | 0.8425 | 0.8851 |
| cross_year_graph | n/a | 0.8296 | 0.6681 | 0.8300 | 0.6702 | 0.7892 | 0.6679 | 0.8396 | 0.7269 | 0.7626 | 0.8684 |
| cross_year_fused | n/a | 0.7709 | 0.6681 | 0.8548 | 0.6445 | 0.7103 | 0.7083 | 0.7796 | 0.7447 | 0.8629 | 0.8851 |
