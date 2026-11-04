# 20261104T010004Z-graph-rag-rq2

- system: `graph-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261030T063140Z-graph-rag-rq2"}`
- git: `4999af0d` (dirty) · wall: 455.4s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8347 ±0.029 | 0.7932 ±0.037 | 0.749 | 0.8374 | 0.7882 | 0.752 | 16 |

Bootstrap 95 % CI of the vote: accuracy 0.772–0.902, macro-F1 0.686–0.876.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 5 / 22 | 0.227 |
| unclear where the gold has a verdict | 10 / 101 | 0.099 |
| verdicts that are right | 86 / 96 | 0.896 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.950 | 0.934 | 0.942 | 61 | 60 |
| failed | 0.885 | 0.676 | 0.767 | 34 | 26 |
| unclear | 0.630 | 0.773 | 0.694 | 22 | 27 |
| disappeared | 0.600 | 1.000 | 0.750 | 6 | 10 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 57, "failed": 2, "unclear": 2, "disappeared": 0}, "failed": {"achieved": 1, "failed": 23, "unclear": 8, "disappeared": 2}, "unclear": {"achieved": 2, "failed": 1, "unclear": 17, "disappeared": 2}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 0, "disappeared": 6}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.682 | 0.522 |
| model_pair | 101 | 0.871 | 0.803 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.7 statements per promise from 2.1 report years; by source {"trajectory:retrieved": 1095, "trajectory:neighbour": 336, "trajectory:linked": 6}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2481 / 839 tokens in / out per promise per repeat; 151 s per repeat; USD 0.55 in all, 1.50 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
