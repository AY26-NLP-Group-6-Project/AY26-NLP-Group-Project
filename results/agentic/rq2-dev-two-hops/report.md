# 20261031T054802Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 123 · split: `dev` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf", "backend": "files", "corpus": "statements", "max_hops": 2, "timeout_s": 90.0, "select": "verified", "prompts": {"rq1_gate": "05cc23d5a014", "rq1_verify": "704bc413c655", "rq2_plan": "8a60f9ec4134"}, "trace_file": "traces-20261031T134807-28936.jsonl"}`
- git: `320a4f17` · wall: 509.1s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7886 ±0.000 | 0.7508 ±0.007 | 0.684 | 0.7886 | 0.7609 | 0.687 | 15 |

Bootstrap 95 % CI of the vote: accuracy 0.715–0.854, macro-F1 0.632–0.848.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 3 / 22 | 0.136 |
| unclear where the gold has a verdict | 21 / 101 | 0.208 |
| verdicts that are right | 78 / 83 | 0.940 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.960 | 0.787 | 0.865 | 61 | 50 |
| failed | 0.929 | 0.765 | 0.839 | 34 | 28 |
| unclear | 0.475 | 0.864 | 0.613 | 22 | 40 |
| disappeared | 0.800 | 0.667 | 0.727 | 6 | 5 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 48, "failed": 1, "unclear": 12, "disappeared": 0}, "failed": {"achieved": 0, "failed": 26, "unclear": 7, "disappeared": 1}, "unclear": {"achieved": 2, "failed": 1, "unclear": 19, "disappeared": 0}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 2, "disappeared": 4}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 22 | 0.682 | 0.525 |
| model_pair | 101 | 0.812 | 0.722 |

## Evidence, speed and cost

- evidence: coverage 1.00, 14.3 statements per promise from 2.0 report years; by source {"agent:hop0:retrieved": 1083, "agent:hop0:neighbour": 336, "agent:hop1:around": 56, "agent:probe": 144, "agent:hop1:search": 83, "agent:hop1:page": 54, "agent:hop2:around": 1, "agent:hop2:page": 1}
- retrieval: p50 5498 ms, p95 10030 ms per promise
- judge: 1.00 calls, 2180 / 832 tokens in / out per promise per repeat; 136 s per repeat; USD 0.53 in all, 1.43 per 1,000 judgements
- planner, on top of the judge: USD 0.84 per 1,000 promises (retrieval runs once per promise)

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| promise_window | 1.30 | 1912 / 379 | 0.193 | 0.000 | {'planner_stop': 118, 'max_hops': 4, 'nothing_new': 1} |

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
