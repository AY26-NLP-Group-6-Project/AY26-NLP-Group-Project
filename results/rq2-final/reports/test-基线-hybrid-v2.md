# 20261031T085152Z-baseline-rag-rq2

- system: `baseline-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf+rerank", "backend": "files"}`
- git: `bfd27d65` · wall: 1257.1s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7560 ±0.011 | 0.6094 ±0.020 | 0.599 | 0.7680 | 0.6367 | 0.618 | 37 |

Bootstrap 95 % CI of the vote: accuracy 0.712–0.816, macro-F1 0.540–0.718.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 15 / 64 | 0.234 |
| unclear where the gold has a verdict | 38 / 186 | 0.204 |
| verdicts that are right | 143 / 163 | 0.877 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.943 | 0.800 | 0.866 | 145 | 123 |
| failed | 0.758 | 0.735 | 0.746 | 34 | 33 |
| unclear | 0.563 | 0.766 | 0.649 | 64 | 87 |
| disappeared | 0.286 | 0.286 | 0.286 | 7 | 7 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 116, "failed": 3, "unclear": 25, "disappeared": 1}, "failed": {"achieved": 1, "failed": 25, "unclear": 8, "disappeared": 0}, "unclear": {"achieved": 6, "failed": 5, "unclear": 49, "disappeared": 4}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 5, "disappeared": 2}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.757 | 0.628 |
| model_pair | 135 | 0.778 | 0.598 |

## Evidence, speed and cost

- evidence: coverage 1.00, 20.0 statements per promise from 2.0 report years; by source {"rrf+rerank": 5000}
- retrieval: p50 833 ms, p95 1429 ms per promise
- judge: 1.00 calls, 2552 / 970 tokens in / out per promise per repeat; 342 s per repeat; USD 1.26 in all, 1.67 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
