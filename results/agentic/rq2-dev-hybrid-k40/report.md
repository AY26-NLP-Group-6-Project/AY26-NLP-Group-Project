# 20261031T053208Z-baseline-rag-rq2

- system: `baseline-rag` · task: `rq2` · condition: `promise_window`, k = 40
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf+rerank", "backend": "files"}`
- git: `320a4f17` · wall: 723.5s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7724 ±0.000 | 0.7307 ±0.015 | 0.659 | 0.7724 | 0.7414 | 0.659 | 21 |

Bootstrap 95 % CI of the vote: accuracy 0.699–0.837, macro-F1 0.617–0.835.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 3 / 22 | 0.136 |
| unclear where the gold has a verdict | 20 / 101 | 0.198 |
| verdicts that are right | 76 / 84 | 0.905 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.926 | 0.820 | 0.870 | 61 | 54 |
| failed | 0.880 | 0.647 | 0.746 | 34 | 25 |
| unclear | 0.487 | 0.864 | 0.623 | 22 | 39 |
| disappeared | 0.800 | 0.667 | 0.727 | 6 | 5 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 50, "failed": 2, "unclear": 9, "disappeared": 0}, "failed": {"achieved": 3, "failed": 22, "unclear": 9, "disappeared": 0}, "unclear": {"achieved": 1, "failed": 1, "unclear": 19, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 2, "disappeared": 4}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.682 | 0.525 |
| model_pair | 101 | 0.792 | 0.688 |

## Evidence, speed and cost

- evidence: coverage 1.00, 40.0 statements per promise from 2.1 report years; by source {"rrf+rerank": 4920}
- retrieval: p50 957 ms, p95 1943 ms per promise
- judge: 1.01 calls, 3754 / 1368 tokens in / out per promise per repeat; 193 s per repeat; USD 0.88 in all, 2.39 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
