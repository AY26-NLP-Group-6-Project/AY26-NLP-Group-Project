# 20261030T063140Z-graph-rag-rq2

- system: `graph-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "graph", "graph_build_id": "dev", "statements": 110314, "unit": "statement"}`
- git: `6b69e6f9` · wall: 432.8s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7913 ±0.005 | 0.7737 ±0.010 | 0.688 | 0.7886 | 0.7692 | 0.685 | 10 |

Bootstrap 95 % CI of the vote: accuracy 0.715–0.854, macro-F1 0.668–0.847.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 5 / 22 | 0.227 |
| unclear where the gold has a verdict | 17 / 101 | 0.168 |
| verdicts that are right | 80 / 89 | 0.899 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.926 | 0.820 | 0.870 | 61 | 54 |
| failed | 0.923 | 0.706 | 0.800 | 34 | 26 |
| unclear | 0.500 | 0.773 | 0.607 | 22 | 34 |
| disappeared | 0.667 | 1.000 | 0.800 | 6 | 9 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 50, "failed": 1, "unclear": 10, "disappeared": 0}, "failed": {"achieved": 2, "failed": 24, "unclear": 7, "disappeared": 1}, "unclear": {"achieved": 2, "failed": 1, "unclear": 17, "disappeared": 2}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 0, "disappeared": 6}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.682 | 0.525 |
| model_pair | 101 | 0.812 | 0.720 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.7 statements per promise from 2.1 report years; by source {"trajectory:retrieved": 1095, "trajectory:neighbour": 336, "trajectory:linked": 6}
- retrieval: p50 261 ms, p95 482 ms per promise
- judge: 1.00 calls, 2031 / 749 tokens in / out per promise per repeat; 130 s per repeat; USD 0.48 in all, 1.30 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
