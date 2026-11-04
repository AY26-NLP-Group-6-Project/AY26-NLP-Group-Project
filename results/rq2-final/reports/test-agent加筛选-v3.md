# 20261031T092745Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "verified-test"}`
- git: `bfd27d65` · wall: 930.2s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7960 ±0.014 | 0.6747 ±0.021 | 0.655 | 0.8080 | 0.6907 | 0.673 | 35 |

Bootstrap 95 % CI of the vote: accuracy 0.760–0.852, macro-F1 0.573–0.782.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 22 / 64 | 0.344 |
| unclear where the gold has a verdict | 23 / 186 | 0.124 |
| verdicts that are right | 160 / 185 | 0.865 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.921 | 0.890 | 0.905 | 145 | 140 |
| failed | 0.737 | 0.824 | 0.778 | 34 | 38 |
| unclear | 0.646 | 0.656 | 0.651 | 64 | 65 |
| disappeared | 0.429 | 0.429 | 0.429 | 7 | 7 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 129, "failed": 3, "unclear": 13, "disappeared": 0}, "failed": {"achieved": 0, "failed": 28, "unclear": 6, "disappeared": 0}, "unclear": {"achieved": 11, "failed": 7, "unclear": 42, "disappeared": 4}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 4, "disappeared": 3}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.809 | 0.707 |
| model_pair | 135 | 0.807 | 0.626 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.5 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2169, "agent:hop1:around": 2, "agent:probe": 9, "agent:hop1:page": 1, "agent:hop1:search": 5}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2450 / 852 tokens in / out per promise per repeat; 310 s per repeat; USD 1.13 in all, 1.51 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
