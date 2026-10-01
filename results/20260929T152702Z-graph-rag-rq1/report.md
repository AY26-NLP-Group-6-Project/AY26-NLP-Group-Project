# 20260929T152702Z-graph-rag-rq1

- system: `graph-rag` · task: `rq1`
- dataset: `gw1000` @ `23dc51f1d9de` · n = 331 · labels: `human_majority` · split: `dev` · repeats: 3
- model: `gpt-5.6-luna` · effort: `low` · temperature: 0.0 · cache: False
- git: `0a62efea` · wall: 889.3s

| condition | macro-F1 (mean ± sd) | micro-F1 | acc | vote macro-F1 | unstable | Δ vs base | flips (pooled) | p (McNemar) | p95 ms | LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | 0.7259 ±0.014 | 0.7531 ±0.010 | 0.7384 ±0.012 | 0.7343 | 40 | — | — | — | 2834.7 | 993 |
| local | 0.7441 ±0.004 | 0.7804 ±0.002 | 0.7737 ±0.004 | 0.7529 | 48 | +0.0182 | +71/-44 | 0.281 | 2848.8 | 993 |
| cross_year_graph | 0.7493 ±0.013 | 0.7723 ±0.009 | 0.7616 ±0.013 | 0.7523 | 42 | +0.0235 | +51/-28 | 0.383 | 2915.7 | 993 |
| cross_year_fused | 0.7664 ±0.016 | 0.7868 ±0.012 | 0.7835 ±0.013 | 0.7810 | 38 | +0.0406 | +76/-44 | 0.058 | 3001.4 | 993 |

## Evidence

| condition | coverage | mean spans | target dropped | by source |
|---|---|---|---|---|
| cross_year_graph | 0.40 | 0.83 | 0 | {'graph:gold_span': 2, 'graph:llm': 8, 'graph:string_match': 266} |
| cross_year_fused | 0.89 | 2.66 | 0 | {'bm25': 603, 'graph:gold_span': 2, 'graph:llm': 8, 'graph:string_match': 266} |

## Per-label F1 (majority vote over repeats)

| condition | implemented | planning | indeterminate | none (detection F1) |
|---|---|---|---|---|
| sentence_only | 0.8192 | 0.7785 | 0.6050 | 0.7664 |
| local | 0.8443 | 0.8219 | 0.5926 | 0.7723 |
| cross_year_graph | 0.8339 | 0.8000 | 0.6230 | 0.7706 |
| cross_year_fused | 0.8399 | 0.8261 | 0.6772 | 0.8081 |

## Bootstrap 95 % CI on macro-F1 (majority vote)

| condition | mean | lo | hi |
|---|---|---|---|
| sentence_only | 0.7310 | 0.6765 | 0.7829 |
| local | 0.7510 | 0.6936 | 0.8061 |
| cross_year_graph | 0.7509 | 0.6947 | 0.8002 |
| cross_year_fused | 0.7794 | 0.7259 | 0.8273 |

## Row type (macro-F1, majority vote)

| condition | aspect (n=266) | no_aspect (n=65) |
|---|---|---|
| sentence_only | 0.7390 | 0.3718 |
| local | 0.7623 | 0.2778 |
| cross_year_graph | 0.7622 | 0.3333 |
| cross_year_fused | 0.7792 | 0.4333 |

## Aspect source (macro-F1, majority vote)

| condition | human_filled (n=10) | llm_proposed (n=266) | none_proposed (n=55) |
|---|---|---|---|
| sentence_only | 0.3718 | 0.7390 | n/a |
| local | 0.2778 | 0.7623 | n/a |
| cross_year_graph | 0.3333 | 0.7622 | n/a |
| cross_year_fused | 0.4333 | 0.7792 | n/a |

## Annotator agreement (macro-F1, majority vote)

| condition | split (n=15) | unanimous (n=316) |
|---|---|---|
| sentence_only | 0.3360 | 0.7559 |
| local | 0.2273 | 0.7809 |
| cross_year_graph | 0.3030 | 0.7748 |
| cross_year_fused | 0.4165 | 0.8010 |

## Aspect category (macro-F1, majority vote)

| condition | (no aspect) (n=54) | business compliance (n=19) | data and cybersecurity protection (n=10) | ecological conservation (n=20) | emissions control (n=41) | management (n=55) | outreach (n=17) | resource optimisation (n=33) | waste management (n=24) | worker & consumer safety compliance (n=31) | workplace (n=27) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sentence_only | n/a | 0.7899 | 0.8030 | 0.6192 | 0.7206 | 0.6365 | 0.7685 | 0.7079 | 0.8857 | 0.6762 | 0.7950 |
| local | n/a | 0.7899 | 0.9030 | 0.9111 | 0.7172 | 0.6130 | 0.7685 | 0.7585 | 0.9441 | 0.5750 | 0.7190 |
| cross_year_graph | n/a | 0.7899 | 0.9153 | 0.7833 | 0.6974 | 0.6216 | 0.7190 | 0.7537 | 0.9043 | 0.6933 | 0.8246 |
| cross_year_fused | n/a | 0.8308 | 0.8222 | 0.7556 | 0.7667 | 0.6863 | 0.8102 | 0.7455 | 0.9441 | 0.7898 | 0.7384 |
