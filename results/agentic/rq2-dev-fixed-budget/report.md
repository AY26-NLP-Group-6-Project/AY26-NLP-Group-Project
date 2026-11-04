# 20261031T054118Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf", "backend": "files", "corpus": "statements", "max_hops": 0, "timeout_s": 90.0, "select": "verified", "prompts": {"rq1_gate": "05cc23d5a014", "rq1_verify": "704bc413c655", "rq2_plan": "8a60f9ec4134"}, "trace_file": "traces-20261031T134123-26852.jsonl"}`
- git: `320a4f17` · wall: 402.2s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7913 ±0.012 | 0.7780 ±0.026 | 0.686 | 0.8130 | 0.7984 | 0.719 | 19 |

Bootstrap 95 % CI of the vote: accuracy 0.748–0.878, macro-F1 0.693–0.874.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 3 / 22 | 0.136 |
| unclear where the gold has a verdict | 16 / 101 | 0.158 |
| verdicts that are right | 81 / 88 | 0.920 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.944 | 0.836 | 0.887 | 61 | 54 |
| failed | 0.893 | 0.735 | 0.806 | 34 | 28 |
| unclear | 0.543 | 0.864 | 0.667 | 22 | 35 |
| disappeared | 0.833 | 0.833 | 0.833 | 6 | 6 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 51, "failed": 2, "unclear": 8, "disappeared": 0}, "failed": {"achieved": 1, "failed": 25, "unclear": 7, "disappeared": 1}, "unclear": {"achieved": 2, "failed": 1, "unclear": 19, "disappeared": 0}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 1, "disappeared": 5}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.727 | 0.593 |
| model_pair | 101 | 0.832 | 0.747 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.6 statements per promise from 2.1 report years; by source {"agent:hop0:retrieved": 1095, "agent:hop0:neighbour": 336}
- retrieval: p50 435 ms, p95 3270 ms per promise
- judge: 1.00 calls, 2026 / 764 tokens in / out per promise per repeat; 129 s per repeat; USD 0.49 in all, 1.32 per 1,000 judgements
- planner, on top of the judge: USD 0.00 per 1,000 promises (retrieval runs once per promise)

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| promise_window | 0.00 | 0 / 0 | 0.000 | 0.000 | {'hop0': 123} |

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
