# 20261031T091030Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261031T085145Z-agentic-rag-rq2"}`
- git: `bfd27d65` · wall: 1033.5s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8173 ±0.017 | 0.6604 ±0.032 | 0.686 | 0.8400 | 0.6950 | 0.724 | 37 |

Bootstrap 95 % CI of the vote: accuracy 0.792–0.884, macro-F1 0.590–0.800.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 18 / 64 | 0.281 |
| unclear where the gold has a verdict | 20 / 186 | 0.108 |
| verdicts that are right | 164 / 184 | 0.891 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.931 | 0.924 | 0.927 | 145 | 144 |
| failed | 0.800 | 0.824 | 0.812 | 34 | 35 |
| unclear | 0.697 | 0.719 | 0.708 | 64 | 66 |
| disappeared | 0.400 | 0.286 | 0.333 | 7 | 5 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 134, "failed": 1, "unclear": 10, "disappeared": 0}, "failed": {"achieved": 0, "failed": 28, "unclear": 6, "disappeared": 0}, "unclear": {"achieved": 9, "failed": 6, "unclear": 46, "disappeared": 3}, "disappeared": {"achieved": 1, "failed": 0, "unclear": 4, "disappeared": 2}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.826 | 0.727 |
| model_pair | 135 | 0.852 | 0.712 |

## Evidence, speed and cost

- evidence: coverage 1.00, 14.0 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2169, "agent:hop1:page": 96, "agent:hop1:around": 82, "agent:probe": 315, "agent:hop1:search": 148, "agent:hop2:page": 9, "agent:hop2:around": 9, "agent:hop2:search": 1}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2611 / 929 tokens in / out per promise per repeat; 344 s per repeat; USD 1.23 in all, 1.64 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
