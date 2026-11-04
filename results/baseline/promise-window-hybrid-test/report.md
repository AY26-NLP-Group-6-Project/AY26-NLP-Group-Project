# 20261104T005711Z-baseline-rag-rq2

- system: `baseline-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf+rerank", "backend": "files"}`
- git: `4999af0d` (dirty) · wall: 1153.6s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7107 ±0.009 | 0.5919 ±0.018 | 0.534 | 0.7080 | 0.5969 | 0.531 | 39 |

Bootstrap 95 % CI of the vote: accuracy 0.652–0.764, macro-F1 0.497–0.678.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 18 / 64 | 0.281 |
| unclear where the gold has a verdict | 49 / 186 | 0.263 |
| verdicts that are right | 131 / 155 | 0.845 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.947 | 0.738 | 0.829 | 145 | 113 |
| failed | 0.677 | 0.618 | 0.646 | 34 | 31 |
| unclear | 0.484 | 0.719 | 0.579 | 64 | 95 |
| disappeared | 0.273 | 0.429 | 0.333 | 7 | 11 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 107, "failed": 4, "unclear": 33, "disappeared": 1}, "failed": {"achieved": 1, "failed": 21, "unclear": 12, "disappeared": 0}, "unclear": {"achieved": 5, "failed": 6, "unclear": 46, "disappeared": 7}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 4, "disappeared": 3}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.704 | 0.560 |
| model_pair | 135 | 0.711 | 0.490 |

## Evidence, speed and cost

- evidence: coverage 1.00, 20.0 statements per promise from 2.0 report years; by source {"rrf+rerank": 5000}
- retrieval: p50 932 ms, p95 1861 ms per promise
- judge: 1.00 calls, 2545 / 956 tokens in / out per promise per repeat; 295 s per repeat; USD 1.24 in all, 1.66 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
