# 20261103T065933Z-agentic-rag-rq1

- system: `agentic-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `bc8e029c` (dirty) · wall: 2177.6s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| cross_year_rrf | 0.7689 ±0.020 | 0.7920 ±0.017 | 0.7920 ±0.017 | 0.7868 | 40 | — | — | — | 3660.3 | 993 |
| cross_year_agentic | 0.7658 ±0.007 | 0.7908 ±0.008 | 0.7908 ±0.008 | 0.7745 | 36 | — | — | — | 3769.1 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| cross_year_rrf | 0.89 | 2.66 | 0 | {'agent:hop0': 879} |
| cross_year_agentic | 0.89 | 2.66 | 0 | {'agent:hop0': 760, 'agent:hop1': 116, 'agent:hop2': 3} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| cross_year_rrf | 11634 / 13302 | 2080 / 3540 | 13806 / 16349 | 3.52 | 989 / 86 | 0.302 | 0 |
| cross_year_agentic | 15876 / 66313 | 2161 / 3637 | 18497 / 68653 | 3.41 | 2314 / 446 | 0.998 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| cross_year_rrf | 1.000 | 1.000 | 23.3 | 1.000 | 1.03 | 0.031 | 0.011 | 0.0 |
| cross_year_agentic | 1.000 | 1.000 | 23.2 | 1.000 | 1.03 | 0.030 | 0.010 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| cross_year_rrf | 0.8454 | 0.8593 | 0.6557 | 0.7333 |
| cross_year_agentic | 0.8472 | 0.8429 | 0.6333 | 0.7045 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| cross_year_rrf | 0.7850 | 0.7276 | 0.8329 |
| cross_year_agentic | 0.7734 | 0.7202 | 0.8247 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| cross_year_rrf | 0.7992 | 0.2619 |
| cross_year_agentic | 0.7861 | 0.2619 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| cross_year_rrf | 0.2619 | 0.7992 | n/a |
| cross_year_agentic | 0.2619 | 0.7861 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| cross_year_rrf | 0.3111 | 0.8123 |
| cross_year_agentic | 0.3111 | 0.7993 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cross_year_rrf | n/a | 0.8308 | 0.9030 | 0.7429 | 0.7924 | 0.6000 | 0.8796 | 0.8098 | 0.9441 | 0.7312 | 0.8246 |
| cross_year_agentic | n/a | 0.8308 | 0.9030 | 0.8487 | 0.7172 | 0.6369 | 0.7725 | 0.7847 | 0.9441 | 0.6933 | 0.8246 |
