# 20261030T063123Z-baseline-rag-rq2

- system: `baseline-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf+rerank", "backend": "files"}`
- git: `6b69e6f9` (dirty) · wall: 541.7s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7832 ±0.009 | 0.7389 ±0.015 | 0.678 | 0.7886 | 0.7712 | 0.684 | 20 |

Bootstrap 95 % CI of the vote: accuracy 0.715–0.862, macro-F1 0.639–0.856.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 3 / 22 | 0.136 |
| unclear where the gold has a verdict | 21 / 101 | 0.208 |
| verdicts that are right | 78 / 83 | 0.940 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.962 | 0.820 | 0.885 | 61 | 52 |
| failed | 0.889 | 0.706 | 0.787 | 34 | 27 |
| unclear | 0.475 | 0.864 | 0.613 | 22 | 40 |
| disappeared | 1.000 | 0.667 | 0.800 | 6 | 4 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 50, "failed": 2, "unclear": 9, "disappeared": 0}, "failed": {"achieved": 0, "failed": 24, "unclear": 10, "disappeared": 0}, "unclear": {"achieved": 2, "failed": 1, "unclear": 19, "disappeared": 0}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 2, "disappeared": 4}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.682 | 0.525 |
| model_pair | 101 | 0.812 | 0.719 |

## Evidence, speed and cost

- evidence: coverage 1.00, 20.0 statements per promise from 2.1 report years; by source {"rrf+rerank": 2460}
- retrieval: p50 641 ms, p95 1295 ms per promise
- judge: 1.00 calls, 2565 / 919 tokens in / out per promise per repeat; 148 s per repeat; USD 0.60 in all, 1.62 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
