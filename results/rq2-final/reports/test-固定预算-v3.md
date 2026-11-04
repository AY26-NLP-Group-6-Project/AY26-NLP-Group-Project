# 20261031T090719Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261031T085149Z-agentic-rag-rq2"}`
- git: `bfd27d65` · wall: 938.1s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7947 ±0.022 | 0.6747 ±0.036 | 0.653 | 0.8080 | 0.6870 | 0.675 | 46 |

Bootstrap 95 % CI of the vote: accuracy 0.756–0.856, macro-F1 0.578–0.776.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 21 / 64 | 0.328 |
| unclear where the gold has a verdict | 25 / 186 | 0.134 |
| verdicts that are right | 159 / 182 | 0.874 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.934 | 0.883 | 0.908 | 145 | 137 |
| failed | 0.757 | 0.824 | 0.789 | 34 | 37 |
| unclear | 0.632 | 0.672 | 0.652 | 64 | 68 |
| disappeared | 0.375 | 0.429 | 0.400 | 7 | 8 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 128, "failed": 2, "unclear": 15, "disappeared": 0}, "failed": {"achieved": 0, "failed": 28, "unclear": 6, "disappeared": 0}, "unclear": {"achieved": 9, "failed": 7, "unclear": 43, "disappeared": 5}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 4, "disappeared": 3}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.791 | 0.680 |
| model_pair | 135 | 0.822 | 0.661 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.5 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2197}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2454 / 848 tokens in / out per promise per repeat; 312 s per repeat; USD 1.13 in all, 1.51 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
