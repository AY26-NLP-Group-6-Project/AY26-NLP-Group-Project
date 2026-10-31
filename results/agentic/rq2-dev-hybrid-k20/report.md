# 20261031T053204Z-baseline-rag-rq2

- system: `baseline-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf+rerank", "backend": "files"}`
- git: `320a4f17` · wall: 599.0s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8022 ±0.031 | 0.7860 ±0.039 | 0.702 | 0.8049 | 0.7877 | 0.706 | 18 |

Bootstrap 95 % CI of the vote: accuracy 0.732–0.870, macro-F1 0.672–0.867.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 5 / 22 | 0.227 |
| unclear where the gold has a verdict | 16 / 101 | 0.158 |
| verdicts that are right | 82 / 90 | 0.911 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.944 | 0.836 | 0.887 | 61 | 54 |
| failed | 0.867 | 0.765 | 0.812 | 34 | 30 |
| unclear | 0.515 | 0.773 | 0.618 | 22 | 33 |
| disappeared | 0.833 | 0.833 | 0.833 | 6 | 6 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 51, "failed": 2, "unclear": 8, "disappeared": 0}, "failed": {"achieved": 1, "failed": 26, "unclear": 7, "disappeared": 0}, "unclear": {"achieved": 2, "failed": 2, "unclear": 17, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 1, "disappeared": 5}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.682 | 0.516 |
| model_pair | 101 | 0.832 | 0.748 |

## Evidence, speed and cost

- evidence: coverage 1.00, 20.0 statements per promise from 2.1 report years; by source {"rrf+rerank": 2460}
- retrieval: p50 967 ms, p95 1913 ms per promise
- judge: 1.00 calls, 2565 / 966 tokens in / out per promise per repeat; 150 s per repeat; USD 0.62 in all, 1.67 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
