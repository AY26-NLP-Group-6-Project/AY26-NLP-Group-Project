# 20261031T091251Z-baseline-rag-rq2

- system: `baseline-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261031T085152Z-baseline-rag-rq2"}`
- git: `bfd27d65` · wall: 1145.7s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8040 ±0.008 | 0.6531 ±0.051 | 0.664 | 0.8160 | 0.6687 | 0.684 | 36 |

Bootstrap 95 % CI of the vote: accuracy 0.768–0.860, macro-F1 0.569–0.755.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 20 / 64 | 0.312 |
| unclear where the gold has a verdict | 23 / 186 | 0.124 |
| verdicts that are right | 160 / 183 | 0.874 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.923 | 0.903 | 0.913 | 145 | 142 |
| failed | 0.771 | 0.794 | 0.783 | 34 | 35 |
| unclear | 0.657 | 0.688 | 0.672 | 64 | 67 |
| disappeared | 0.333 | 0.286 | 0.308 | 7 | 6 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 131, "failed": 2, "unclear": 11, "disappeared": 1}, "failed": {"achieved": 0, "failed": 27, "unclear": 7, "disappeared": 0}, "unclear": {"achieved": 11, "failed": 6, "unclear": 44, "disappeared": 3}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 5, "disappeared": 2}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.765 | 0.637 |
| model_pair | 135 | 0.859 | 0.724 |

## Evidence, speed and cost

- evidence: coverage 1.00, 20.0 statements per promise from 2.0 report years; by source {"rrf+rerank": 5000}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 3102 / 1069 tokens in / out per promise per repeat; 381 s per repeat; USD 1.43 in all, 1.90 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
