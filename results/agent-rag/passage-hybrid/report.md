# 20261020T142347Z-agentic-rag-rq1

- system: `agentic-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `label` · prompt `action_classifier.md` @ `4af9b84b0a68`
- git: `b32494b8` (dirty) · wall: 2403.7s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7241 ±0.004 | 0.7534 ±0.004 | 0.7397 ±0.004 | 0.7227 | 41 | — | — | — | 2463.1 | 993 |
| local | 0.7532 ±0.019 | 0.7865 ±0.016 | 0.7822 ±0.017 | 0.7457 | 45 | +0.0291 | +78/-45 | 0.073 | 2566.7 | 993 |
| same_report_rrf | 0.7244 ±0.021 | 0.7587 ±0.019 | 0.7555 ±0.019 | 0.7287 | 46 | +0.0003 | +75/-97 | 0.419 | 2918.4 | 993 |
| cross_year_rrf | 0.7624 ±0.009 | 0.7941 ±0.007 | 0.7908 ±0.008 | 0.7688 | 48 | +0.0382 | +73/-61 | 0.268 | 2895.5 | 993 |
| cross_year_agentic | 0.7502 ±0.005 | 0.7827 ±0.004 | 0.7798 ±0.006 | 0.7555 | 41 | +0.0260 | +67/-70 | 1.000 | 3299.2 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 3.00 | 0 | {'agent:hop0': 993} |
| cross_year_rrf | 0.89 | 2.66 | 0 | {'agent:hop0': 879} |
| cross_year_agentic | 0.89 | 2.66 | 0 | {'agent:hop0': 839, 'agent:hop1': 38, 'agent:hop2': 2} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 1477 / 2365 | 1477 / 2365 | 4.92 | 394 / 9 | 0.090 | 0 |
| local | — / — | 1565 / 2777 | 1565 / 2777 | 4.62 | 506 / 24 | 0.129 | 0 |
| same_report_rrf | 7852 / 8727 | 1637 / 2800 | 9547 / 11309 | 4.41 | 899 / 31 | 0.217 | 0 |
| cross_year_rrf | 7306 / 8302 | 1617 / 2741 | 8997 / 10468 | 4.50 | 839 / 27 | 0.201 | 0 |
| cross_year_agentic | 10026 / 43453 | 1702 / 3114 | 11903 / 45496 | 4.20 | 1654 / 253 | 0.634 | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8222 | 0.7838 | 0.5620 | 0.7778 |
| local | 0.8414 | 0.8138 | 0.5818 | 0.8462 |
| same_report_rrf | 0.8231 | 0.7941 | 0.5690 | 0.6742 |
| cross_year_rrf | 0.8601 | 0.8201 | 0.6261 | 0.7391 |
| cross_year_agentic | 0.8454 | 0.8058 | 0.6154 | 0.6667 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7197 | 0.6624 | 0.7720 |
| local | 0.7443 | 0.6885 | 0.7978 |
| same_report_rrf | 0.7271 | 0.6684 | 0.7846 |
| cross_year_rrf | 0.7677 | 0.7076 | 0.8186 |
| cross_year_agentic | 0.7534 | 0.6947 | 0.8080 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7257 | 0.3718 |
| local | 0.7437 | 0.3714 |
| same_report_rrf | 0.7321 | 0.3162 |
| cross_year_rrf | 0.7739 | 0.3385 |
| cross_year_agentic | 0.7556 | 0.3714 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3718 | 0.7257 | n/a |
| local | 0.3714 | 0.7437 | n/a |
| same_report_rrf | 0.3162 | 0.7321 | n/a |
| cross_year_rrf | 0.3385 | 0.7739 | n/a |
| cross_year_agentic | 0.3714 | 0.7556 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.4141 | 0.7395 |
| local | 0.2929 | 0.7696 |
| same_report_rrf | 0.2424 | 0.7547 |
| cross_year_rrf | 0.4141 | 0.7885 |
| cross_year_agentic | 0.4141 | 0.7743 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.7899 | 0.7333 | 0.6734 | 0.6924 | 0.6380 | 0.7685 | 0.7206 | 0.8470 | 0.6504 | 0.7822 |
| local | n/a | 0.7899 | 0.8030 | 0.9111 | 0.6922 | 0.6087 | 0.7685 | 0.7265 | 0.9441 | 0.7028 | 0.7190 |
| same_report_rrf | n/a | 0.8756 | 0.9030 | 0.7821 | 0.6882 | 0.5638 | 0.8045 | 0.7247 | 0.8279 | 0.7194 | 0.6746 |
| cross_year_rrf | n/a | 0.8308 | 0.9030 | 0.8487 | 0.6880 | 0.6320 | 0.6796 | 0.8358 | 0.8857 | 0.7312 | 0.8246 |
| cross_year_agentic | n/a | 0.7596 | 0.9030 | 0.7464 | 0.6868 | 0.6320 | 0.8677 | 0.7507 | 0.8857 | 0.7222 | 0.8246 |
