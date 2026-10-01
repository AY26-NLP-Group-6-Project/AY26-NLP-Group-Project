# 20260930T004540Z-baseline-rag-rq1

- system: `baseline-rag` · task: `rq1`
- dataset: `gw1000` @ `23dc51f1d9de` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- git: `69c0a9f3` · wall: 665.4s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7331 ±0.006 | 0.7598 ±0.004 | 0.7445 ±0.006 | 0.7416 | 43 | — | — | — | 2669.8 | 993 |
| same_report_rrf | 0.7584 ±0.002 | 0.7878 ±0.003 | 0.7835 ±0.002 | 0.7648 | 42 | +0.0253 | +79/-52 | 0.256 | 2752.9 | 993 |
| cross_year_rrf | 0.7424 ±0.011 | 0.7759 ±0.006 | 0.7689 ±0.006 | 0.7510 | 45 | +0.0093 | +64/-49 | 0.711 | 2293.7 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 2.14 | 286 | {'rrf+rerank': 707} |
| cross_year_rrf | 0.89 | 2.66 | 0 | {'rrf+rerank': 879} |

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8339 | 0.8027 | 0.5882 | 0.7636 |
| same_report_rrf | 0.8374 | 0.8310 | 0.6261 | 0.8200 |
| cross_year_rrf | 0.8421 | 0.8227 | 0.5882 | 0.7879 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7379 | 0.6835 | 0.7908 |
| same_report_rrf | 0.7635 | 0.7086 | 0.8172 |
| cross_year_rrf | 0.7489 | 0.6946 | 0.8001 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7440 | 0.3718 |
| same_report_rrf | 0.7708 | 0.3162 |
| cross_year_rrf | 0.7545 | 0.3385 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3718 | 0.7440 | n/a |
| same_report_rrf | 0.3162 | 0.7708 | n/a |
| cross_year_rrf | 0.3385 | 0.7545 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.4141 | 0.7597 |
| same_report_rrf | 0.3111 | 0.7894 |
| cross_year_rrf | 0.2333 | 0.7774 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.7899 | 0.8030 | 0.6343 | 0.7188 | 0.6442 | 0.8677 | 0.7612 | 0.7667 | 0.7063 | 0.7822 |
| same_report_rrf | n/a | 0.7899 | 0.9030 | 0.8381 | 0.7630 | 0.6387 | 0.8102 | 0.7657 | 0.8944 | 0.6680 | 0.7708 |
| cross_year_rrf | n/a | 0.7596 | 0.7333 | 0.7349 | 0.7162 | 0.6109 | 0.8677 | 0.8098 | 0.8857 | 0.6946 | 0.7708 |
