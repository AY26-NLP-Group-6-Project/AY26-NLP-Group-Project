# 20261031T061753Z-agentic-rag-rq1

- system: `agentic-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `c3a297f8` · wall: 458.1s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| company_agentic | 0.7638 ±0.007 | 0.7835 ±0.004 | 0.7835 ±0.004 | 0.7629 | 35 | — | — | — | 2747.6 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| company_agentic | 0.22 | 0.65 | 0 | {'agent:hop1': 216} |

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| company_agentic | 1.22 | 547 / 120 | 1.000 | 0.782 | {'no_gap': 259, 'resolved': 46, 'unresolved': 26} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| company_agentic | 1971 / 7562 | 1716 / 2915 | 3803 / 10275 | 3.41 | 1121 / 189 | 0.451 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| company_agentic | 1.000 | 1.000 | 21.9 | 1.000 | 1.02 | 0.069 | 0.023 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| company_agentic | 0.8310 | 0.8286 | 0.6290 | 0.8000 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| company_agentic | 0.7597 | 0.7054 | 0.8096 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| company_agentic | 0.7638 | 0.3714 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| company_agentic | 0.3714 | 0.7638 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| company_agentic | 0.3111 | 0.7867 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| company_agentic | n/a | 0.8308 | 0.9030 | 0.7919 | 0.7162 | 0.6445 | 0.8102 | 0.7295 | 0.8279 | 0.7312 | 0.8246 |
