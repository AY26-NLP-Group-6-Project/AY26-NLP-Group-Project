# 20261103T082156Z-agentic-rag-rq1

- system: `agentic-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `393260c2` (dirty) · wall: 2254.7s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| cross_year_rrf | 0.7677 ±0.010 | 0.7920 ±0.006 | 0.7920 ±0.006 | 0.7694 | 34 | — | — | — | 3854.1 | 993 |
| cross_year_agentic | 0.7757 ±0.017 | 0.7981 ±0.015 | 0.7981 ±0.015 | 0.7894 | 37 | — | — | — | 3881.4 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| cross_year_rrf | 0.89 | 2.66 | 0 | {'agent:hop0': 879} |
| cross_year_agentic | 0.89 | 2.66 | 0 | {'agent:hop0': 744, 'agent:hop1': 124, 'agent:hop2': 11} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| cross_year_rrf | 11600 / 13257 | 2252 / 3781 | 13817 / 16661 | 3.31 | 989 / 88 | 0.304 | 0 |
| cross_year_agentic | 16926 / 66874 | 2206 / 3832 | 19539 / 69280 | 3.34 | 2323 / 449 | 1.004 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| cross_year_rrf | 1.000 | 1.000 | 23.3 | 1.000 | 1.04 | 0.036 | 0.014 | 0.0 |
| cross_year_agentic | 1.000 | 1.000 | 23.3 | 1.000 | 1.03 | 0.034 | 0.011 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| cross_year_rrf | 0.8407 | 0.8467 | 0.6207 | 0.7191 |
| cross_year_agentic | 0.8522 | 0.8382 | 0.6777 | 0.7191 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| cross_year_rrf | 0.7677 | 0.7091 | 0.8178 |
| cross_year_agentic | 0.7881 | 0.7328 | 0.8381 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| cross_year_rrf | 0.7806 | 0.2619 |
| cross_year_agentic | 0.7976 | 0.3162 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| cross_year_rrf | 0.2619 | 0.7806 | n/a |
| cross_year_agentic | 0.3162 | 0.7976 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| cross_year_rrf | 0.3111 | 0.7943 |
| cross_year_agentic | 0.2929 | 0.8151 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cross_year_rrf | n/a | 0.8308 | 0.9030 | 0.7894 | 0.7691 | 0.6125 | 0.7725 | 0.7745 | 0.9441 | 0.7028 | 0.7708 |
| cross_year_agentic | n/a | 0.8308 | 0.9030 | 0.8487 | 0.7630 | 0.6267 | 0.7685 | 0.7717 | 0.9441 | 0.8328 | 0.8246 |
