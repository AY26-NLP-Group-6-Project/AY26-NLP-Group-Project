# 20261031T074646Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261031T054802Z-agentic-rag-rq2"}`
- git: `e77707da` · wall: 435.9s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8428 ±0.017 | 0.7969 ±0.030 | 0.760 | 0.8537 | 0.8046 | 0.775 | 21 |

Bootstrap 95 % CI of the vote: accuracy 0.789–0.911, macro-F1 0.697–0.884.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 6 / 22 | 0.273 |
| unclear where the gold has a verdict | 9 / 101 | 0.089 |
| verdicts that are right | 89 / 98 | 0.908 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.966 | 0.934 | 0.950 | 61 | 59 |
| failed | 0.844 | 0.794 | 0.818 | 34 | 32 |
| unclear | 0.640 | 0.727 | 0.681 | 22 | 25 |
| disappeared | 0.714 | 0.833 | 0.769 | 6 | 7 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 57, "failed": 2, "unclear": 2, "disappeared": 0}, "failed": {"achieved": 0, "failed": 27, "unclear": 6, "disappeared": 1}, "unclear": {"achieved": 2, "failed": 3, "unclear": 16, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 1, "disappeared": 5}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.773 | 0.660 |
| model_pair | 101 | 0.871 | 0.801 |

## Evidence, speed and cost

- evidence: coverage 1.00, 14.3 statements per promise from 2.0 report years; by source {"agent:hop0:retrieved": 1083, "agent:hop0:neighbour": 336, "agent:hop1:around": 56, "agent:probe": 144, "agent:hop1:search": 83, "agent:hop1:page": 54, "agent:hop2:around": 1, "agent:hop2:page": 1}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2539 / 912 tokens in / out per promise per repeat; 145 s per repeat; USD 0.59 in all, 1.60 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
