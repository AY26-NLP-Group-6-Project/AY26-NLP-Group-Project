# 20261031T074637Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261031T054802Z-agentic-rag-rq2"}`
- git: `e77707da` · wall: 436.4s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8374 ±0.008 | 0.7713 ±0.009 | 0.750 | 0.8374 | 0.7731 | 0.750 | 11 |

Bootstrap 95 % CI of the vote: accuracy 0.772–0.902, macro-F1 0.641–0.865.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 5 / 22 | 0.227 |
| unclear where the gold has a verdict | 11 / 101 | 0.109 |
| verdicts that are right | 86 / 95 | 0.905 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.949 | 0.918 | 0.933 | 61 | 59 |
| failed | 0.867 | 0.765 | 0.812 | 34 | 30 |
| unclear | 0.607 | 0.773 | 0.680 | 22 | 28 |
| disappeared | 0.667 | 0.667 | 0.667 | 6 | 6 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 56, "failed": 2, "unclear": 3, "disappeared": 0}, "failed": {"achieved": 1, "failed": 26, "unclear": 6, "disappeared": 1}, "unclear": {"achieved": 2, "failed": 2, "unclear": 17, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 2, "disappeared": 4}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.818 | 0.718 |
| model_pair | 101 | 0.842 | 0.758 |

## Evidence, speed and cost

- evidence: coverage 1.00, 14.3 statements per promise from 2.0 report years; by source {"agent:hop0:retrieved": 1083, "agent:hop0:neighbour": 336, "agent:hop1:around": 56, "agent:probe": 144, "agent:hop1:search": 83, "agent:hop1:page": 54, "agent:hop2:around": 1, "agent:hop2:page": 1}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2643 / 906 tokens in / out per promise per repeat; 145 s per repeat; USD 0.60 in all, 1.62 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
