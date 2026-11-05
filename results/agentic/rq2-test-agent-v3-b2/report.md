# 20261105T150953Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261105T144054Z-agentic-rag-rq2"}`
- git: `b8868d3a` (dirty) · wall: 1163.7s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7840 ±0.018 | 0.6160 ±0.036 | 0.636 | 0.8000 | 0.6329 | 0.660 | 48 |

Bootstrap 95 % CI of the vote: accuracy 0.748–0.848, macro-F1 0.541–0.732.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 21 / 64 | 0.328 |
| unclear where the gold has a verdict | 24 / 186 | 0.129 |
| verdicts that are right | 157 / 183 | 0.858 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.942 | 0.903 | 0.923 | 145 | 139 |
| failed | 0.667 | 0.706 | 0.686 | 34 | 36 |
| unclear | 0.642 | 0.672 | 0.656 | 64 | 67 |
| disappeared | 0.250 | 0.286 | 0.267 | 7 | 8 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 131, "failed": 2, "unclear": 9, "disappeared": 3}, "failed": {"achieved": 0, "failed": 24, "unclear": 10, "disappeared": 0}, "unclear": {"achieved": 8, "failed": 10, "unclear": 43, "disappeared": 3}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 5, "disappeared": 2}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.765 | 0.639 |
| model_pair | 135 | 0.830 | 0.672 |

## Evidence, speed and cost

- evidence: coverage 1.00, 16.5 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2129, "agent:hop1:page": 222, "agent:hop1:around": 346, "agent:probe": 315, "agent:hop1:search": 329, "agent:hop2:search": 41, "agent:hop2:page": 31, "agent:hop2:around": 29}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2749 / 984 tokens in / out per promise per repeat; 388 s per repeat; USD 1.30 in all, 1.73 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
