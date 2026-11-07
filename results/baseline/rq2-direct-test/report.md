# 20261107T084650Z-direct-rq2

- system: `direct` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `direct` · prompt `promise_outcome_direct.md` @ `fbf6e2039c56` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"baseline": "direct", "evidence": "none"}`
- git: `937c2665` (dirty) · wall: 291.5s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.2987 ±0.002 | 0.1469 ±0.006 | 0.033 | 0.2840 | 0.1293 | 0.022 | 30 |

Bootstrap 95 % CI of the vote: accuracy 0.232–0.344, macro-F1 0.105–0.157.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 1 / 64 | 0.016 |
| unclear where the gold has a verdict | 178 / 186 | 0.957 |
| verdicts that are right | 8 / 9 | 0.889 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.889 | 0.055 | 0.104 | 145 | 9 |
| failed | 0.000 | 0.000 | 0.000 | 34 | 0 |
| unclear | 0.261 | 0.984 | 0.413 | 64 | 241 |
| disappeared | 0.000 | 0.000 | 0.000 | 7 | 0 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 8, "failed": 0, "unclear": 137, "disappeared": 0}, "failed": {"achieved": 0, "failed": 0, "unclear": 34, "disappeared": 0}, "unclear": {"achieved": 1, "failed": 0, "unclear": 63, "disappeared": 0}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 7, "disappeared": 0}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.252 | 0.010 |
| model_pair | 135 | 0.311 | 0.033 |

## Evidence, speed and cost

- evidence: coverage 0.00, 0.0 statements per promise from 0.0 report years; by source {}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 368 / 187 tokens in / out per promise per repeat; 97 s per repeat; USD 0.22 in all, 0.30 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
