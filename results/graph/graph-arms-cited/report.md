# 20261029T143232Z-graph-rag-rq1

- system: `graph-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `b3d06731` (dirty) · wall: 1616.4s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7450 ±0.014 | 0.7703 ±0.012 | 0.7689 ±0.012 | 0.7498 | 34 | — | — | — | 8589.5 | 993 |
| local | 0.7529 ±0.004 | 0.7822 ±0.002 | 0.7822 ±0.002 | 0.7512 | 30 | +0.0078 | +45/-51 | 1.000 | 4851.4 | 993 |
| cross_year_graph | 0.7472 ±0.010 | 0.7724 ±0.010 | 0.7701 ±0.011 | 0.7449 | 29 | +0.0021 | +22/-25 | 0.774 | 5575.6 | 993 |
| cross_year_fused | 0.7708 ±0.006 | 0.7910 ±0.004 | 0.7895 ±0.004 | 0.7668 | 33 | +0.0258 | +45/-35 | 1.000 | 5053.9 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| cross_year_graph | 0.40 | 0.83 | 0 | {'graph:gold_span': 2, 'graph:llm': 8, 'graph:string_match': 266} |
| cross_year_fused | 0.89 | 2.66 | 0 | {'bm25': 603, 'graph:gold_span': 2, 'graph:llm': 8, 'graph:string_match': 266} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 2734 / 5837 | 2734 / 5837 | 2.55 | 540 / 88 | 0.214 | 0 |
| local | — / — | 2770 / 4725 | 2770 / 4725 | 2.68 | 656 / 100 | 0.251 | 0 |
| cross_year_graph | 9 / 11 | 2988 / 5199 | 2991 / 5207 | 2.41 | 584 / 92 | 0.227 | 0 |
| cross_year_fused | 20 / 88 | 3118 / 4901 | 3152 / 4918 | 2.39 | 680 / 97 | 0.253 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 17.9 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 18.7 | 1.000 | 1.07 | — | — | 0.0 |
| cross_year_graph | 1.000 | 1.000 | 18.2 | 1.000 | 1.01 | 0.013 | 0.006 | 0.0 |
| cross_year_fused | 1.000 | 1.000 | 18.6 | 1.000 | 1.01 | 0.010 | 0.003 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8198 | 0.8058 | 0.6240 | 0.7527 |
| local | 0.8367 | 0.8235 | 0.5932 | 0.7045 |
| cross_year_graph | 0.8227 | 0.8201 | 0.5920 | 0.7312 |
| cross_year_fused | 0.8327 | 0.8321 | 0.6357 | 0.7111 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7475 | 0.6952 | 0.8013 |
| local | 0.7493 | 0.6913 | 0.8051 |
| cross_year_graph | 0.7433 | 0.6877 | 0.7985 |
| cross_year_fused | 0.7654 | 0.7128 | 0.8183 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7556 | 0.3162 |
| local | 0.7612 | 0.2619 |
| cross_year_graph | 0.7496 | 0.3162 |
| cross_year_fused | 0.7733 | 0.3162 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3162 | 0.7556 | n/a |
| local | 0.2619 | 0.7612 | n/a |
| cross_year_graph | 0.3162 | 0.7496 | n/a |
| cross_year_fused | 0.3162 | 0.7733 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.4165 | 0.7680 |
| local | 0.4165 | 0.7697 |
| cross_year_graph | 0.2929 | 0.7683 |
| cross_year_fused | 0.3111 | 0.7907 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.8308 | 0.9030 | 0.7464 | 0.7616 | 0.5448 | 0.8102 | 0.6894 | 0.9441 | 0.7194 | 0.7959 |
| local | n/a | 0.8308 | 0.9030 | 0.8422 | 0.7656 | 0.5396 | 0.8796 | 0.8214 | 0.8557 | 0.6680 | 0.6794 |
| cross_year_graph | n/a | 0.8308 | 0.9030 | 0.7299 | 0.7162 | 0.6057 | 0.8677 | 0.6894 | 0.9043 | 0.6732 | 0.7959 |
| cross_year_fused | n/a | 0.8308 | 0.9030 | 0.7429 | 0.7656 | 0.6448 | 0.8796 | 0.6894 | 0.8671 | 0.6946 | 0.8414 |
