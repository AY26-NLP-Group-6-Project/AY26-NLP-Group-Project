# 20261104T024056Z-baseline-rag-rq2

- system: `baseline-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261104T005711Z-baseline-rag-rq2"}`
- git: `fe8fed89` (dirty) · wall: 942.6s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7520 ±0.012 | 0.6230 ±0.019 | 0.587 | 0.7480 | 0.6098 | 0.580 | 46 |

Bootstrap 95 % CI of the vote: accuracy 0.696–0.800, macro-F1 0.526–0.693.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 27 / 64 | 0.422 |
| unclear where the gold has a verdict | 33 / 186 | 0.177 |
| verdicts that are right | 150 / 180 | 0.833 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.925 | 0.848 | 0.885 | 145 | 133 |
| failed | 0.727 | 0.706 | 0.716 | 34 | 33 |
| unclear | 0.529 | 0.578 | 0.552 | 64 | 70 |
| disappeared | 0.214 | 0.429 | 0.286 | 7 | 14 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 123, "failed": 2, "unclear": 19, "disappeared": 1}, "failed": {"achieved": 0, "failed": 24, "unclear": 10, "disappeared": 0}, "unclear": {"achieved": 10, "failed": 7, "unclear": 37, "disappeared": 10}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 4, "disappeared": 3}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.722 | 0.573 |
| model_pair | 135 | 0.770 | 0.577 |

## Evidence, speed and cost

- evidence: coverage 1.00, 20.0 statements per promise from 2.0 report years; by source {"rrf+rerank": 5000}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 3098 / 1052 tokens in / out per promise per repeat; 314 s per repeat; USD 1.41 in all, 1.88 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
