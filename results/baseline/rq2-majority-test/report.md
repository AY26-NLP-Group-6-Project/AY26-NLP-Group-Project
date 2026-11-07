# 20261107T084427Z-majority-rq2

- system: `majority` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 1
- judge: `majority` · prompt `None` @ `None` · model: `?` · effort: `?`
- retriever: `{"baseline": "majority", "evidence": "none"}`
- git: `937c2665` (dirty) · wall: 0.7s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.5800 ±0.000 | 0.1835 ±0.000 | 0.000 | 0.5800 | 0.1835 | 0.000 | None |

Bootstrap 95 % CI of the vote: accuracy 0.520–0.644, macro-F1 0.171–0.196.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 64 / 64 | 1.000 |
| unclear where the gold has a verdict | 0 / 186 | 0.000 |
| verdicts that are right | 145 / 250 | 0.580 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.580 | 1.000 | 0.734 | 145 | 250 |
| failed | 0.000 | 0.000 | 0.000 | 34 | 0 |
| unclear | 0.000 | 0.000 | 0.000 | 64 | 0 |
| disappeared | 0.000 | 0.000 | 0.000 | 7 | 0 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 145, "failed": 0, "unclear": 0, "disappeared": 0}, "failed": {"achieved": 34, "failed": 0, "unclear": 0, "disappeared": 0}, "unclear": {"achieved": 64, "failed": 0, "unclear": 0, "disappeared": 0}, "disappeared": {"achieved": 7, "failed": 0, "unclear": 0, "disappeared": 0}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.513 | 0.000 |
| model_pair | 135 | 0.637 | 0.000 |

## Evidence, speed and cost

- evidence: coverage 0.00, 0.0 statements per promise from 0.0 report years; by source {}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 0.00 calls, 0 / 0 tokens in / out per promise per repeat; 0 s per repeat; USD 0.00 in all, 0.00 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
