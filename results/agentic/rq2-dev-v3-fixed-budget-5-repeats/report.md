# 20261031T081043Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 5
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261031T054118Z-agentic-rag-rq2"}`
- git: `0eb8a27d` · wall: 725.2s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8472 ±0.018 | 0.7977 ±0.019 | 0.767 | 0.8618 | 0.8067 | 0.789 | 23 |

Bootstrap 95 % CI of the vote: accuracy 0.797–0.919, macro-F1 0.699–0.893.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 4 / 22 | 0.182 |
| unclear where the gold has a verdict | 8 / 101 | 0.079 |
| verdicts that are right | 88 / 97 | 0.907 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.966 | 0.934 | 0.950 | 61 | 59 |
| failed | 0.867 | 0.765 | 0.812 | 34 | 30 |
| unclear | 0.692 | 0.818 | 0.750 | 22 | 26 |
| disappeared | 0.625 | 0.833 | 0.714 | 6 | 8 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 57, "failed": 3, "unclear": 1, "disappeared": 0}, "failed": {"achieved": 0, "failed": 26, "unclear": 6, "disappeared": 2}, "unclear": {"achieved": 2, "failed": 1, "unclear": 18, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 1, "disappeared": 5}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.818 | 0.718 |
| model_pair | 101 | 0.871 | 0.804 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.6 statements per promise from 2.1 report years; by source {"agent:hop0:retrieved": 1095, "agent:hop0:neighbour": 336}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2474 / 833 tokens in / out per promise per repeat; 145 s per repeat; USD 0.92 in all, 1.49 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
