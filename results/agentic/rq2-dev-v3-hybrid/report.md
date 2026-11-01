# 20261031T074643Z-baseline-rag-rq2

- system: `baseline-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261031T053204Z-baseline-rag-rq2"}`
- git: `e77707da` · wall: 480.2s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8211 ±0.008 | 0.7744 ±0.014 | 0.726 | 0.8130 | 0.7703 | 0.712 | 15 |

Bootstrap 95 % CI of the vote: accuracy 0.740–0.878, macro-F1 0.655–0.854.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 6 / 22 | 0.273 |
| unclear where the gold has a verdict | 12 / 101 | 0.119 |
| verdicts that are right | 84 / 95 | 0.884 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.918 | 0.918 | 0.918 | 61 | 61 |
| failed | 0.852 | 0.676 | 0.754 | 34 | 27 |
| unclear | 0.571 | 0.727 | 0.640 | 22 | 28 |
| disappeared | 0.714 | 0.833 | 0.769 | 6 | 7 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 56, "failed": 2, "unclear": 3, "disappeared": 0}, "failed": {"achieved": 2, "failed": 23, "unclear": 8, "disappeared": 1}, "unclear": {"achieved": 3, "failed": 2, "unclear": 16, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 1, "disappeared": 5}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.773 | 0.647 |
| model_pair | 101 | 0.822 | 0.726 |

## Evidence, speed and cost

- evidence: coverage 1.00, 20.0 statements per promise from 2.1 report years; by source {"rrf+rerank": 2460}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 3111 / 1048 tokens in / out per promise per repeat; 160 s per repeat; USD 0.69 in all, 1.88 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
