# 20261105T144119Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261105T142304Z-agentic-rag-rq2"}`
- git: `b8868d3a` (dirty) · wall: 1269.2s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7720 ±0.016 | 0.6372 ±0.035 | 0.624 | 0.7680 | 0.6309 | 0.616 | 40 |

Bootstrap 95 % CI of the vote: accuracy 0.720–0.820, macro-F1 0.552–0.711.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 22 / 64 | 0.344 |
| unclear where the gold has a verdict | 29 / 186 | 0.156 |
| verdicts that are right | 150 / 179 | 0.838 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.938 | 0.841 | 0.887 | 145 | 130 |
| failed | 0.694 | 0.735 | 0.714 | 34 | 36 |
| unclear | 0.592 | 0.656 | 0.622 | 64 | 71 |
| disappeared | 0.231 | 0.429 | 0.300 | 7 | 13 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 122, "failed": 4, "unclear": 16, "disappeared": 3}, "failed": {"achieved": 0, "failed": 25, "unclear": 9, "disappeared": 0}, "unclear": {"achieved": 8, "failed": 7, "unclear": 42, "disappeared": 7}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 4, "disappeared": 3}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.739 | 0.602 |
| model_pair | 135 | 0.793 | 0.620 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.5 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2197}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2454 / 864 tokens in / out per promise per repeat; 423 s per repeat; USD 1.15 in all, 1.53 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
