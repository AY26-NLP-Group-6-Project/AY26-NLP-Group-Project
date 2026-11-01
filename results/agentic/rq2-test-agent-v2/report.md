# 20261031T085145Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf", "backend": "files", "corpus": "statements", "max_hops": 2, "timeout_s": 90.0, "select": "verified", "prompts": {"rq1_gate": "05cc23d5a014", "rq1_verify": "704bc413c655", "rq2_plan": "8a60f9ec4134"}, "trace_file": "traces-20261031T165151-14652.jsonl"}`
- git: `bfd27d65` · wall: 1122.7s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7733 ±0.018 | 0.6478 ±0.068 | 0.622 | 0.7840 | 0.6412 | 0.638 | 43 |

Bootstrap 95 % CI of the vote: accuracy 0.732–0.836, macro-F1 0.550–0.756.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 12 / 64 | 0.188 |
| unclear where the gold has a verdict | 40 / 186 | 0.215 |
| verdicts that are right | 144 / 158 | 0.911 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.929 | 0.807 | 0.863 | 145 | 126 |
| failed | 0.867 | 0.765 | 0.812 | 34 | 30 |
| unclear | 0.565 | 0.812 | 0.667 | 64 | 92 |
| disappeared | 0.500 | 0.143 | 0.222 | 7 | 2 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 117, "failed": 1, "unclear": 27, "disappeared": 0}, "failed": {"achieved": 1, "failed": 26, "unclear": 7, "disappeared": 0}, "unclear": {"achieved": 8, "failed": 3, "unclear": 52, "disappeared": 1}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 6, "disappeared": 1}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.774 | 0.652 |
| model_pair | 135 | 0.793 | 0.616 |

## Evidence, speed and cost

- evidence: coverage 1.00, 14.0 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2169, "agent:hop1:page": 96, "agent:hop1:around": 82, "agent:probe": 315, "agent:hop1:search": 148, "agent:hop2:page": 9, "agent:hop2:around": 9, "agent:hop2:search": 1}
- retrieval: p50 5235 ms, p95 10543 ms per promise
- judge: 1.00 calls, 2154 / 839 tokens in / out per promise per repeat; 308 s per repeat; USD 1.08 in all, 1.44 per 1,000 judgements
- planner, on top of the judge: USD 0.81 per 1,000 promises (retrieval runs once per promise)

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| promise_window | 1.27 | 1825 / 373 | 0.188 | 0.000 | {'planner_stop': 237, 'max_hops': 9, 'nothing_new': 4} |

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
