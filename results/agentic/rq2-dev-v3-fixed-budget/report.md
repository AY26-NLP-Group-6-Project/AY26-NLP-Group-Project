# 20261031T074640Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "20261031T054118Z-agentic-rag-rq2"}`
- git: `e77707da` · wall: 420.5s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8591 ±0.012 | 0.8069 ±0.018 | 0.784 | 0.8699 | 0.8263 | 0.800 | 17 |

Bootstrap 95 % CI of the vote: accuracy 0.813–0.927, macro-F1 0.720–0.908.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 4 / 22 | 0.182 |
| unclear where the gold has a verdict | 8 / 101 | 0.079 |
| verdicts that are right | 89 / 97 | 0.918 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.950 | 0.934 | 0.942 | 61 | 60 |
| failed | 0.900 | 0.794 | 0.844 | 34 | 30 |
| unclear | 0.692 | 0.818 | 0.750 | 22 | 26 |
| disappeared | 0.714 | 0.833 | 0.769 | 6 | 7 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 57, "failed": 2, "unclear": 2, "disappeared": 0}, "failed": {"achieved": 1, "failed": 27, "unclear": 5, "disappeared": 1}, "unclear": {"achieved": 2, "failed": 1, "unclear": 18, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 1, "disappeared": 5}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.818 | 0.718 |
| model_pair | 101 | 0.881 | 0.817 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.6 statements per promise from 2.1 report years; by source {"agent:hop0:retrieved": 1095, "agent:hop0:neighbour": 336}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2474 / 833 tokens in / out per promise per repeat; 140 s per repeat; USD 0.55 in all, 1.49 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
