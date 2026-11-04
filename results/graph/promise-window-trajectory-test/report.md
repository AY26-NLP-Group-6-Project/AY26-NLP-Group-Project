# 20261104T005955Z-graph-rag-rq2

- system: `graph-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-6-luna` · effort: `low`
- retriever: `{"store": "graph", "graph_build_id": "dev", "statements": 110314, "unit": "statement"}`
- git: `4999af0d` (dirty) · wall: 850.5s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7293 ±0.013 | 0.5726 ±0.050 | 0.563 | 0.7360 | 0.5475 | 0.572 | 44 |

Bootstrap 95 % CI of the vote: accuracy 0.680–0.792, macro-F1 0.499–0.594.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 11 / 64 | 0.172 |
| unclear where the gold has a verdict | 51 / 186 | 0.274 |
| verdicts that are right | 131 / 146 | 0.897 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.964 | 0.745 | 0.840 | 145 | 112 |
| failed | 0.767 | 0.676 | 0.719 | 34 | 30 |
| unclear | 0.510 | 0.828 | 0.631 | 64 | 104 |
| disappeared | 0.000 | 0.000 | 0.000 | 7 | 4 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 108, "failed": 2, "unclear": 33, "disappeared": 2}, "failed": {"achieved": 0, "failed": 23, "unclear": 11, "disappeared": 0}, "unclear": {"achieved": 4, "failed": 5, "unclear": 53, "disappeared": 2}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 7, "disappeared": 0}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.739 | 0.606 |
| model_pair | 135 | 0.733 | 0.529 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.6 statements per promise from 2.0 report years; by source {"trajectory:retrieved": 2197, "trajectory:neighbour": 694, "trajectory:linked": 4}
- retrieval: p50 220 ms, p95 440 ms per promise
- judge: 1.00 calls, 2022 / 772 tokens in / out per promise per repeat; 258 s per repeat; USD 1.00 in all, 1.33 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
