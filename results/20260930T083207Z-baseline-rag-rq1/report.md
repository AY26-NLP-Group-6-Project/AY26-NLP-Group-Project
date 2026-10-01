# 20260930T083207Z-baseline-rag-rq1

- system: `baseline-rag` · task: `rq1`
- dataset: `gw1000` @ `3e18cc14e648` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- classifier: `cited` · prompt `action_classifier_cited.md` @ `f79137d448e4`
- git: `426779b2` · wall: 1159.0s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7553 ±0.009 | 0.7771 ±0.007 | 0.7762 ±0.008 | 0.7647 | 43 | — | — | — | 3258.4 | 993 |
| local | 0.7449 ±0.006 | 0.7754 ±0.005 | 0.7749 ±0.004 | 0.7519 | 44 | -0.0104 | +57/-52 | 1.000 | 3255.3 | 993 |
| same_report_rrf | 0.7492 ±0.013 | 0.7762 ±0.011 | 0.7762 ±0.011 | 0.7550 | 27 | -0.0060 | +46/-38 | 1.000 | 3410.0 | 993 |
| cross_year_rrf | 0.7657 ±0.005 | 0.7871 ±0.006 | 0.7871 ±0.006 | 0.7804 | 40 | +0.0104 | +62/-45 | 0.281 | 3137.7 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| same_report_rrf | 1.00 | 2.14 | 286 | {'rrf+rerank': 707} |
| cross_year_rrf | 0.89 | 2.66 | 0 | {'rrf+rerank': 879} |

## Speed and cost (mean over repeats)

| condition | retrieval p50 / p95 ms | classify p50 / p95 ms | end-to-end p50 / p95 ms | items/s | tokens in / out per item | USD per 1k items | cached calls |
|---|---|---|---|---|---|---|---|
| sentence_only | — / — | 1703 / 2906 | 1703 / 2906 | 4.26 | 540 / 63 | prices not set | 0 |
| local | — / — | 1844 / 3259 | 1844 / 3259 | 3.95 | 656 / 79 | prices not set | 0 |
| same_report_rrf | 326 / 433 | 2000 / 3299 | 2347 / 3631 | 3.77 | 653 / 92 | prices not set | 0 |
| cross_year_rrf | 117 / 175 | 1942 / 3119 | 2048 / 3254 | 3.85 | 675 / 84 | prices not set | 0 |

Latency is per call; items/s is wall-clock throughput at the classifier's concurrency.

## Rationale and citations (mean over repeats)

| condition | format ok | has rationale | words | cites target | citations / item | evidence used | spans cited | invalid refs |
|---|---|---|---|---|---|---|---|---|
| sentence_only | 1.000 | 1.000 | 21.7 | 1.000 | 1.00 | — | — | 0.0 |
| local | 1.000 | 1.000 | 22.9 | 1.000 | 1.07 | — | — | 0.0 |
| same_report_rrf | 1.000 | 1.000 | 22.7 | 1.000 | 1.09 | 0.074 | 0.040 | 0.0 |
| cross_year_rrf | 0.999 | 0.999 | 22.6 | 0.999 | 1.02 | 0.020 | 0.007 | 0.0 |

`evidence used` = share of items that had retrieved evidence and cited at least one span of it; `spans cited` = share of all shown spans that were cited.

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8239 | 0.8571 | 0.6129 | 0.8000 |
| local | 0.8339 | 0.8235 | 0.5983 | 0.8247 |
| same_report_rrf | 0.8288 | 0.8261 | 0.6102 | 0.8247 |
| cross_year_rrf | 0.8403 | 0.8235 | 0.6774 | 0.8367 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7620 | 0.7102 | 0.8155 |
| local | 0.7505 | 0.6903 | 0.8042 |
| same_report_rrf | 0.7535 | 0.6956 | 0.8080 |
| cross_year_rrf | 0.7788 | 0.7232 | 0.8282 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7650 | 0.3714 |
| local | 0.7567 | 0.3162 |
| same_report_rrf | 0.7603 | 0.3162 |
| cross_year_rrf | 0.7885 | 0.3162 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3714 | 0.7650 | n/a |
| local | 0.3162 | 0.7567 | n/a |
| same_report_rrf | 0.3162 | 0.7603 | n/a |
| cross_year_rrf | 0.3162 | 0.7885 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.3111 | 0.7889 |
| local | 0.3111 | 0.7757 |
| same_report_rrf | 0.3111 | 0.7789 |
| cross_year_rrf | 0.2273 | 0.8090 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.7899 | 0.9030 | 0.7486 | 0.7143 | 0.6973 | 0.8796 | 0.7745 | 0.8279 | 0.7213 | 0.7384 |
| local | n/a | 0.8308 | 0.9030 | 0.8615 | 0.6462 | 0.6145 | 0.8796 | 0.7657 | 0.8944 | 0.7312 | 0.7084 |
| same_report_rrf | n/a | 0.8308 | 0.9030 | 0.7180 | 0.6989 | 0.6646 | 0.7354 | 0.7431 | 0.9441 | 0.6933 | 0.7708 |
| cross_year_rrf | n/a | 0.8308 | 1.0000 | 0.7547 | 0.7662 | 0.6145 | 0.8102 | 0.7717 | 0.9441 | 0.7855 | 0.7708 |
