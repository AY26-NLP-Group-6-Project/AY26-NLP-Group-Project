# 20261107T084426Z-majority-rq2

- system: `majority` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 1
- judge: `majority` · prompt `None` @ `None` · model: `?` · effort: `?`
- retriever: `{"baseline": "majority", "evidence": "none"}`
- git: `937c2665` (dirty) · wall: 0.4s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.4959 ±0.000 | 0.1658 ±0.000 | 0.000 | 0.4959 | 0.1658 | 0.000 | None |

Bootstrap 95 % CI of the vote: accuracy 0.407–0.593, macro-F1 0.145–0.186.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 22 / 22 | 1.000 |
| unclear where the gold has a verdict | 0 / 101 | 0.000 |
| verdicts that are right | 61 / 123 | 0.496 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.496 | 1.000 | 0.663 | 61 | 123 |
| failed | 0.000 | 0.000 | 0.000 | 34 | 0 |
| unclear | 0.000 | 0.000 | 0.000 | 22 | 0 |
| disappeared | 0.000 | 0.000 | 0.000 | 6 | 0 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 61, "failed": 0, "unclear": 0, "disappeared": 0}, "failed": {"achieved": 34, "failed": 0, "unclear": 0, "disappeared": 0}, "unclear": {"achieved": 22, "failed": 0, "unclear": 0, "disappeared": 0}, "disappeared": {"achieved": 6, "failed": 0, "unclear": 0, "disappeared": 0}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.500 | 0.000 |
| model_pair | 101 | 0.495 | 0.000 |

## Evidence, speed and cost

- evidence: coverage 0.00, 0.0 statements per promise from 0.0 report years; by source {}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 0.00 calls, 0 / 0 tokens in / out per promise per repeat; 0 s per repeat; USD 0.00 in all, 0.00 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
