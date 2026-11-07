# 20261107T084428Z-direct-rq2

- system: `direct` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `direct` · prompt `promise_outcome_direct.md` @ `fbf6e2039c56` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"baseline": "direct", "evidence": "none"}`
- git: `937c2665` (dirty) · wall: 140.5s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.2114 ±0.024 | 0.1124 ±0.025 | 0.026 | 0.1951 | 0.0928 | 0.014 | 12 |

Bootstrap 95 % CI of the vote: accuracy 0.130–0.260, macro-F1 0.061–0.128.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 0 / 22 | 0.000 |
| unclear where the gold has a verdict | 99 / 101 | 0.980 |
| verdicts that are right | 2 / 2 | 1.000 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 1.000 | 0.033 | 0.063 | 61 | 2 |
| failed | 0.000 | 0.000 | 0.000 | 34 | 0 |
| unclear | 0.182 | 1.000 | 0.308 | 22 | 121 |
| disappeared | 0.000 | 0.000 | 0.000 | 6 | 0 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 2, "failed": 0, "unclear": 59, "disappeared": 0}, "failed": {"achieved": 0, "failed": 0, "unclear": 34, "disappeared": 0}, "unclear": {"achieved": 0, "failed": 0, "unclear": 22, "disappeared": 0}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 6, "disappeared": 0}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.227 | 0.000 |
| model_pair | 101 | 0.188 | 0.016 |

## Evidence, speed and cost

- evidence: coverage 0.00, 0.0 statements per promise from 0.0 report years; by source {}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 368 / 183 tokens in / out per promise per repeat; 47 s per repeat; USD 0.11 in all, 0.29 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
