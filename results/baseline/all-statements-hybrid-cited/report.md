# 20261004T080206Z-baseline-rag-rq1

- system: `baseline-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `92f2ea65` (dirty) · wall: 1580.4s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7583 ±0.007 | 0.7788 ±0.006 | 0.7774 ±0.006 | 0.7686 | 40 | — | — | — | 4227.3 | 993 |
| same_report_rrf | 0.7535 ±0.008 | 0.7779 ±0.010 | 0.7774 ±0.010 | 0.7591 | 36 | -0.0048 | +49/-55 | 0.711 | 3501.0 | 993 |
| cross_year_rrf | 0.7759 ±0.015 | 0.7981 ±0.013 | 0.7981 ±0.013 | 0.7722 | 44 | +0.0176 | +56/-44 | 1.000 | 6987.3 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 2.00 | 331 | {'rrf+rerank': 662} |
| cross_year_rrf | 0.89 | 2.66 | 0 | {'rrf+rerank': 879} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 2120 / 4202 | 2120 / 4202 | 3.25 | 540 / 63 | 0.184 | 0 |
| same_report_rrf | 925 / 2054 | 2214 / 3535 | 3273 / 4976 | 3.41 | 665 / 90 | 0.242 | 0 |
| cross_year_rrf | 408 / 1695 | 2832 / 5830 | 3423 / 6696 | 2.44 | 692 / 85 | 0.240 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 22.0 | 1.000 | 1.00 | — | — | 0.0 |
| same_report_rrf | 1.000 | 1.000 | 23.0 | 1.000 | 1.12 | 0.109 | 0.062 | 0.0 |
| cross_year_rrf | 1.000 | 1.000 | 22.8 | 1.000 | 1.02 | 0.020 | 0.008 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8406 | 0.8194 | 0.6457 | 0.8163 |
| same_report_rrf | 0.8299 | 0.8321 | 0.6154 | 0.8000 |
| cross_year_rrf | 0.8462 | 0.8201 | 0.6504 | 0.8000 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7656 | 0.7122 | 0.8134 |
| same_report_rrf | 0.7566 | 0.6998 | 0.8089 |
| cross_year_rrf | 0.7696 | 0.7150 | 0.8169 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7704 | 0.3714 |
| same_report_rrf | 0.7646 | 0.3162 |
| cross_year_rrf | 0.7741 | 0.3714 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3714 | 0.7704 | n/a |
| same_report_rrf | 0.3162 | 0.7646 | n/a |
| cross_year_rrf | 0.3714 | 0.7741 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.2929 | 0.7926 |
| same_report_rrf | 0.3111 | 0.7834 |
| cross_year_rrf | 0.2929 | 0.7968 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.8308 | 0.9030 | 0.6809 | 0.7352 | 0.6617 | 0.8677 | 0.7847 | 0.8857 | 0.6762 | 0.8246 |
| same_report_rrf | n/a | 0.8308 | 0.7778 | 0.7894 | 0.7662 | 0.6084 | 0.8102 | 0.7504 | 0.8944 | 0.7028 | 0.7708 |
| cross_year_rrf | n/a | 0.8308 | 0.9030 | 0.7919 | 0.7667 | 0.6320 | 0.8102 | 0.7087 | 0.9441 | 0.7194 | 0.7708 |
