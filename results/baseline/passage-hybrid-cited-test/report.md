# 20261105T112934Z-baseline-rag-rq1

> **Test split.** Open it once, for the final report; tune on `dev`.

- system: `baseline-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 669 · labels: `human_majority` · split: `test` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `68b57e8c` (dirty) · wall: 3516.0s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7644 ±0.013 | 0.7845 ±0.013 | 0.7824 ±0.013 | 0.7642 | 76 | — | — | — | 4505.6 | 2007 |
| local | 0.7613 ±0.002 | 0.7858 ±0.002 | 0.7842 ±0.002 | 0.7704 | 85 | -0.0031 | +86/-137 | 0.101 | 3666.9 | 2007 |
| same_report_rrf | 0.7350 ±0.012 | 0.7615 ±0.010 | 0.7590 ±0.011 | 0.7385 | 98 | -0.0295 | +78/-175 | 0.001 | 3761.6 | 2007 |
| cross_year_rrf | 0.7580 ±0.009 | 0.7787 ±0.008 | 0.7776 ±0.008 | 0.7740 | 110 | -0.0065 | +91/-159 | 0.135 | 3758.1 | 2007 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 1.91 | 728 | {'rrf+rerank': 1279} |
| cross_year_rrf | 0.90 | 2.70 | 0 | {'rrf+rerank': 1803} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 2009 / 4064 | 2009 / 4064 | 3.47 | 540 / 86 | 0.211 | 0 |
| local | — / — | 2120 / 3762 | 2120 / 3762 | 3.41 | 657 / 94 | 0.244 | 0 |
| same_report_rrf | 1124 / 1299 | 2089 / 3971 | 3215 / 5079 | 3.42 | 866 / 89 | 0.280 | 0 |
| cross_year_rrf | 832 / 950 | 1887 / 3486 | 2628 / 4275 | 3.78 | 998 / 78 | 0.293 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 17.9 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 19.0 | 1.000 | 1.06 | — | — | 0.0 |
| same_report_rrf | 1.000 | 1.000 | 19.9 | 1.000 | 1.05 | 0.047 | 0.026 | 0.0 |
| cross_year_rrf | 1.000 | 1.000 | 20.2 | 1.000 | 1.02 | 0.023 | 0.008 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8374 | 0.7601 | 0.6950 | 0.8300 |
| local | 0.8522 | 0.7842 | 0.6747 | 0.6966 |
| same_report_rrf | 0.8262 | 0.7491 | 0.6403 | 0.7039 |
| cross_year_rrf | 0.8406 | 0.7749 | 0.7063 | 0.7191 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7632 | 0.7231 | 0.8007 |
| local | 0.7697 | 0.7322 | 0.8074 |
| same_report_rrf | 0.7373 | 0.6975 | 0.7761 |
| cross_year_rrf | 0.7731 | 0.7362 | 0.8119 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=537) | no_aspect (n=132) |
|---|---|---|
| sentence_only | 0.7681 | 0.6117 |
| local | 0.7743 | 0.6178 |
| same_report_rrf | 0.7402 | 0.6117 |
| cross_year_rrf | 0.7785 | 0.6117 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=24) | llm_proposed (n=537) | none_proposed (n=108) |
|---|---|---|---|
| sentence_only | 0.6117 | 0.7681 | n/a |
| local | 0.6178 | 0.7743 | n/a |
| same_report_rrf | 0.6117 | 0.7402 | n/a |
| cross_year_rrf | 0.6117 | 0.7785 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=1) | unanimous (n=668) |
|---|---|---|
| sentence_only | n/a | 0.7642 |
| local | n/a | 0.7704 |
| same_report_rrf | n/a | 0.7385 |
| cross_year_rrf | n/a | 0.7740 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=107) | business compliance (n=42) | data and cybersecurity protection (n=24) | ecological conservation (n=41) | emissions control (n=79) | management (n=116) | outreach (n=36) | resource optimisation (n=53) | waste management (n=48) | worker & consumer safety compliance (n=69) | workplace (n=54) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.7655 | 0.6681 | 0.8040 | 0.6738 | 0.7549 | 0.7463 | 0.7893 | 0.7456 | 0.8266 | 0.8462 |
| local | n/a | 0.8048 | 0.6795 | 0.8216 | 0.7082 | 0.7193 | 0.7411 | 0.7998 | 0.7250 | 0.7869 | 0.9044 |
| same_report_rrf | n/a | 0.8124 | 0.6905 | 0.7551 | 0.6321 | 0.7411 | 0.7004 | 0.7617 | 0.7038 | 0.7040 | 0.8851 |
| cross_year_rrf | n/a | 0.8504 | 0.6528 | 0.7985 | 0.6696 | 0.7525 | 0.7485 | 0.7856 | 0.7456 | 0.8589 | 0.8657 |
