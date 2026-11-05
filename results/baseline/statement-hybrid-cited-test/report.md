# 20261105T103924Z-baseline-rag-rq1

> **Test split.** Open it once, for the final report; tune on `dev`.

- system: `baseline-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 669 · labels: `human_majority` · split: `test` · repeats: 3
- model: `gpt-6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `12d04c7b` (dirty) · wall: 2990.7s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7620 ±0.012 | 0.7840 ±0.011 | 0.7824 ±0.012 | 0.7644 | 57 | — | — | — | 3451.0 | 2007 |
| local | 0.7639 ±0.007 | 0.7886 ±0.006 | 0.7872 ±0.007 | 0.7701 | 75 | +0.0019 | +72/-125 | 0.043 | 3479.5 | 2007 |
| same_report_rrf | 0.7672 ±0.008 | 0.7912 ±0.006 | 0.7908 ±0.007 | 0.7731 | 74 | +0.0053 | +78/-114 | 0.134 | 4690.8 | 2007 |
| cross_year_rrf | 0.7577 ±0.007 | 0.7784 ±0.006 | 0.7782 ±0.006 | 0.7662 | 85 | -0.0043 | +66/-120 | 0.044 | 3846.4 | 2007 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 2.00 | 672 | {'rrf+rerank': 1335} |
| cross_year_rrf | 0.90 | 2.70 | 0 | {'rrf+rerank': 1803} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 1986 / 3398 | 1986 / 3398 | 3.66 | 540 / 86 | 0.211 | 0 |
| local | — / — | 2136 / 3514 | 2136 / 3514 | 3.51 | 657 / 97 | 0.247 | 0 |
| same_report_rrf | 500 / 1131 | 2274 / 5039 | 2884 / 5657 | 3.03 | 667 / 103 | 0.257 | 0 |
| cross_year_rrf | 173 / 836 | 2179 / 4121 | 2455 / 4418 | 3.23 | 697 / 95 | 0.253 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 17.9 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 19.1 | 1.000 | 1.07 | — | — | 0.0 |
| same_report_rrf | 1.000 | 1.000 | 19.3 | 1.000 | 1.09 | 0.081 | 0.043 | 0.0 |
| cross_year_rrf | 1.000 | 1.000 | 19.1 | 1.000 | 1.02 | 0.019 | 0.006 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8414 | 0.7798 | 0.6719 | 0.8325 |
| local | 0.8513 | 0.7766 | 0.6825 | 0.6932 |
| same_report_rrf | 0.8527 | 0.7737 | 0.6929 | 0.7232 |
| cross_year_rrf | 0.8414 | 0.7518 | 0.7054 | 0.7303 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7634 | 0.7248 | 0.8000 |
| local | 0.7694 | 0.7306 | 0.8073 |
| same_report_rrf | 0.7724 | 0.7347 | 0.8092 |
| cross_year_rrf | 0.7651 | 0.7256 | 0.8027 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=537) | no_aspect (n=132) |
|---|---|---|
| sentence_only | 0.7681 | 0.6178 |
| local | 0.7748 | 0.6032 |
| same_report_rrf | 0.7753 | 0.6279 |
| cross_year_rrf | 0.7703 | 0.5824 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=24) | llm_proposed (n=537) | none_proposed (n=108) |
|---|---|---|---|
| sentence_only | 0.6178 | 0.7681 | n/a |
| local | 0.6032 | 0.7748 | n/a |
| same_report_rrf | 0.6279 | 0.7753 | n/a |
| cross_year_rrf | 0.5824 | 0.7703 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=1) | unanimous (n=668) |
|---|---|---|
| sentence_only | n/a | 0.7644 |
| local | n/a | 0.7701 |
| same_report_rrf | n/a | 0.7731 |
| cross_year_rrf | n/a | 0.7662 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=107) | business compliance (n=42) | data and cybersecurity protection (n=24) | ecological conservation (n=41) | emissions control (n=79) | management (n=116) | outreach (n=36) | resource optimisation (n=53) | waste management (n=48) | worker & consumer safety compliance (n=69) | workplace (n=54) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.8318 | 0.6681 | 0.8300 | 0.6992 | 0.7144 | 0.6785 | 0.8209 | 0.7219 | 0.8159 | 0.8462 |
| local | n/a | 0.8048 | 0.5762 | 0.8181 | 0.6947 | 0.7329 | 0.7083 | 0.8643 | 0.7436 | 0.8425 | 0.8438 |
| same_report_rrf | n/a | 0.8660 | 0.6681 | 0.8509 | 0.6557 | 0.7286 | 0.7083 | 0.8360 | 0.7835 | 0.8425 | 0.8628 |
| cross_year_rrf | n/a | 0.7433 | 0.6610 | 0.8490 | 0.6567 | 0.7579 | 0.7083 | 0.7796 | 0.7652 | 0.8412 | 0.8684 |
