# 20261104T022653Z-graph-rag-rq2

- system: `graph-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261104T005955Z-graph-rag-rq2"}`
- git: `fe8fed89` (dirty) · wall: 827.9s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7947 ±0.016 | 0.6573 ±0.043 | 0.658 | 0.8040 | 0.6683 | 0.673 | 36 |

Bootstrap 95 % CI of the vote: accuracy 0.756–0.852, macro-F1 0.578–0.754.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 18 / 64 | 0.281 |
| unclear where the gold has a verdict | 27 / 186 | 0.145 |
| verdicts that are right | 155 / 177 | 0.876 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.955 | 0.869 | 0.910 | 145 | 132 |
| failed | 0.788 | 0.765 | 0.776 | 34 | 33 |
| unclear | 0.630 | 0.719 | 0.672 | 64 | 73 |
| disappeared | 0.250 | 0.429 | 0.316 | 7 | 12 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 126, "failed": 1, "unclear": 15, "disappeared": 3}, "failed": {"achieved": 0, "failed": 26, "unclear": 8, "disappeared": 0}, "unclear": {"achieved": 6, "failed": 6, "unclear": 46, "disappeared": 6}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 4, "disappeared": 3}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.765 | 0.640 |
| model_pair | 135 | 0.837 | 0.698 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.6 statements per promise from 2.0 report years; by source {"trajectory:retrieved": 2197, "trajectory:neighbour": 694, "trajectory:linked": 4}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2462 / 854 tokens in / out per promise per repeat; 276 s per repeat; USD 1.14 in all, 1.52 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
