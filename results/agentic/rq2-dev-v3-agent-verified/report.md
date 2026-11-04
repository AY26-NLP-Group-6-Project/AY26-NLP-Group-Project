# 20261031T081040Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v3` · prompt `promise_outcome_v3.md` @ `01a3a075315f` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"evidence_from": "agent_verified"}`
- git: `0eb8a27d` · wall: 481.2s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.8537 ±0.022 | 0.8051 ±0.051 | 0.775 | 0.8618 | 0.8134 | 0.789 | 17 |

Bootstrap 95 % CI of the vote: accuracy 0.797–0.919, macro-F1 0.706–0.895.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 5 / 22 | 0.227 |
| unclear where the gold has a verdict | 9 / 101 | 0.089 |
| verdicts that are right | 89 / 97 | 0.918 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.983 | 0.934 | 0.958 | 61 | 58 |
| failed | 0.844 | 0.794 | 0.818 | 34 | 32 |
| unclear | 0.654 | 0.773 | 0.708 | 22 | 26 |
| disappeared | 0.714 | 0.833 | 0.769 | 6 | 7 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 57, "failed": 2, "unclear": 2, "disappeared": 0}, "failed": {"achieved": 0, "failed": 27, "unclear": 6, "disappeared": 1}, "unclear": {"achieved": 1, "failed": 3, "unclear": 17, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 1, "disappeared": 5}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.773 | 0.647 |
| model_pair | 101 | 0.881 | 0.819 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.7 statements per promise from 2.0 report years; by source {"agent:hop0:retrieved": 1083, "agent:hop0:neighbour": 336, "agent:probe": 9, "agent:hop1:page": 3, "agent:hop1:around": 3, "agent:hop1:search": 2}
- retrieval: p50 0 ms, p95 0 ms per promise
- judge: 1.00 calls, 2480 / 826 tokens in / out per promise per repeat; 160 s per repeat; USD 0.55 in all, 1.49 per 1,000 judgements

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
