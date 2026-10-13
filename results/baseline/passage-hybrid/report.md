# 20260929T150108Z-baseline-rag-rq1

- system: `baseline-rag` · task: `rq1`
- dataset: `gw1000` @ `23dc51f1d9de` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- git: `0a62efea` · wall: 1552.1s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7471 ±0.011 | 0.7704 ±0.007 | 0.7591 ±0.010 | 0.7591 | 41 | — | — | — | 2660.3 | 993 |
| local | 0.7458 ±0.016 | 0.7770 ±0.013 | 0.7737 ±0.015 | 0.7640 | 47 | -0.0013 | +67/-64 | 1.000 | 2702.1 | 993 |
| same_report_rrf | 0.7335 ±0.026 | 0.7655 ±0.025 | 0.7603 ±0.024 | 0.7484 | 51 | -0.0136 | +58/-90 | 0.174 | 4409.9 | 993 |
| cross_year_rrf | 0.7409 ±0.012 | 0.7736 ±0.009 | 0.7689 ±0.011 | 0.7464 | 54 | -0.0062 | +56/-90 | 0.040 | 2805.8 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 1.91 | 361 | {'rrf+rerank': 632} |
| cross_year_rrf | 0.89 | 2.66 | 0 | {'rrf+rerank': 879} |

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8370 | 0.8163 | 0.6240 | 0.7885 |
| local | 0.8403 | 0.8310 | 0.6207 | 0.7835 |
| same_report_rrf | 0.8299 | 0.8271 | 0.5882 | 0.6889 |
| cross_year_rrf | 0.8414 | 0.8116 | 0.5862 | 0.5977 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7564 | 0.7039 | 0.8102 |
| local | 0.7609 | 0.7085 | 0.8108 |
| same_report_rrf | 0.7462 | 0.6904 | 0.8046 |
| cross_year_rrf | 0.7445 | 0.6872 | 0.7970 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7649 | 0.3718 |
| local | 0.7742 | 0.2778 |
| same_report_rrf | 0.7572 | 0.2778 |
| cross_year_rrf | 0.7543 | 0.3000 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3718 | 0.7649 | n/a |
| local | 0.2778 | 0.7742 | n/a |
| same_report_rrf | 0.2778 | 0.7572 | n/a |
| cross_year_rrf | 0.3000 | 0.7543 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.4104 | 0.7787 |
| local | 0.2273 | 0.7922 |
| same_report_rrf | 0.3111 | 0.7720 |
| cross_year_rrf | 0.3030 | 0.7692 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.7899 | 0.8030 | 0.7845 | 0.7346 | 0.6364 | 0.7685 | 0.7472 | 0.9441 | 0.6775 | 0.8246 |
| local | n/a | 0.8308 | 0.9030 | 0.8054 | 0.7412 | 0.5964 | 0.8677 | 0.6995 | 1.0000 | 0.7028 | 0.7708 |
| same_report_rrf | n/a | 0.8308 | 0.9030 | 0.8251 | 0.7359 | 0.6185 | 0.8796 | 0.7145 | 0.8944 | 0.6775 | 0.6794 |
| cross_year_rrf | n/a | 0.7596 | 0.8030 | 0.8251 | 0.7127 | 0.5880 | 0.7685 | 0.7996 | 0.8279 | 0.8016 | 0.7384 |
