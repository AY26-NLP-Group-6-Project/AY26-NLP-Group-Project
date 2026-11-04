# 20261031T062526Z-agentic-rag-rq1

- system: `agentic-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `c3a297f8` · wall: 346.0s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| company_agentic | 0.7757 ±0.005 | 0.7968 ±0.006 | 0.7968 ±0.006 | 0.7814 | 36 | — | — | — | 3196.1 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| company_agentic | 0.22 | 0.66 | 0 | {'agent:hop1': 219} |

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| company_agentic | 1.00 | 432 / 90 | 1.000 | 0.779 | {'no_gap': 258, 'max_hops': 73} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| company_agentic | 1948 / 4638 | 1712 / 3079 | 3734 / 7409 | 4.15 | 1008 / 161 | 0.395 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| company_agentic | 1.000 | 1.000 | 22.0 | 1.000 | 1.02 | 0.078 | 0.030 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| company_agentic | 0.8472 | 0.8467 | 0.6504 | 0.7742 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| company_agentic | 0.7789 | 0.7255 | 0.8294 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| company_agentic | 0.7834 | 0.3714 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| company_agentic | 0.3714 | 0.7834 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| company_agentic | 0.3111 | 0.8065 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| company_agentic | n/a | 0.7899 | 0.9030 | 0.8387 | 0.7172 | 0.6841 | 0.8796 | 0.8098 | 0.8279 | 0.7460 | 0.7708 |
