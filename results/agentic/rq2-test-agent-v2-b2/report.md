# 20261105T144054Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf", "backend": "files", "corpus": "statements", "max_hops": 2, "timeout_s": 90.0, "select": "verified", "prompts": {"rq1_gate": "05cc23d5a014", "rq1_verify": "704bc413c655", "rq2_plan": "8a60f9ec4134"}, "trace_file": "traces-20261105T224057-28196.jsonl"}`
- git: `b8868d3a` (dirty) · wall: 1720.0s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7347 ±0.008 | 0.5722 ±0.021 | 0.569 | 0.7440 | 0.5724 | 0.583 | 51 |

Bootstrap 95 % CI of the vote: accuracy 0.692–0.796, macro-F1 0.499–0.657.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 16 / 64 | 0.250 |
| unclear where the gold has a verdict | 44 / 186 | 0.237 |
| verdicts that are right | 138 / 158 | 0.873 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.975 | 0.793 | 0.875 | 145 | 118 |
| failed | 0.667 | 0.647 | 0.657 | 34 | 33 |
| unclear | 0.522 | 0.750 | 0.615 | 64 | 92 |
| disappeared | 0.143 | 0.143 | 0.143 | 7 | 7 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 115, "failed": 2, "unclear": 26, "disappeared": 2}, "failed": {"achieved": 0, "failed": 22, "unclear": 12, "disappeared": 0}, "unclear": {"achieved": 3, "failed": 9, "unclear": 48, "disappeared": 4}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 6, "disappeared": 1}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.722 | 0.580 |
| model_pair | 135 | 0.763 | 0.576 |

## Evidence, speed and cost

- evidence: coverage 1.00, 16.5 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2129, "agent:hop1:page": 222, "agent:hop1:around": 346, "agent:probe": 315, "agent:hop1:search": 329, "agent:hop2:search": 41, "agent:hop2:page": 31, "agent:hop2:around": 29}
- retrieval: p50 11549 ms, p95 55286 ms per promise
- judge: 1.00 calls, 2286 / 906 tokens in / out per promise per repeat; 394 s per repeat; USD 1.16 in all, 1.54 per 1,000 judgements
- planner, on top of the judge: USD 1.13 per 1,000 promises (retrieval runs once per promise)

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| promise_window | 1.80 | 2662 / 501 | 0.318 | 0.000 | {'planner_stop': 163, 'max_hops': 70, 'nothing_new': 15, 'timeout': 2} |

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
