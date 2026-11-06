# 20261105T142304Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf", "backend": "files", "corpus": "statements", "max_hops": 0, "timeout_s": 90.0, "select": "verified", "prompts": {"rq1_gate": "05cc23d5a014", "rq1_verify": "704bc413c655", "rq2_plan": "8a60f9ec4134"}, "trace_file": "traces-20261105T222307-25896.jsonl"}`
- git: `b8868d3a` · wall: 967.6s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7320 ±0.004 | 0.6305 ±0.012 | 0.572 | 0.7480 | 0.6453 | 0.596 | 42 |

Bootstrap 95 % CI of the vote: accuracy 0.696–0.800, macro-F1 0.544–0.731.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 12 / 64 | 0.188 |
| unclear where the gold has a verdict | 45 / 186 | 0.242 |
| verdicts that are right | 135 / 153 | 0.882 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.973 | 0.745 | 0.844 | 145 | 111 |
| failed | 0.727 | 0.706 | 0.716 | 34 | 33 |
| unclear | 0.536 | 0.812 | 0.646 | 64 | 97 |
| disappeared | 0.333 | 0.429 | 0.375 | 7 | 9 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 108, "failed": 4, "unclear": 31, "disappeared": 2}, "failed": {"achieved": 0, "failed": 24, "unclear": 10, "disappeared": 0}, "unclear": {"achieved": 3, "failed": 5, "unclear": 52, "disappeared": 4}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 4, "disappeared": 3}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.730 | 0.598 |
| model_pair | 135 | 0.763 | 0.584 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.5 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2197}
- retrieval: p50 568 ms, p95 2908 ms per promise
- judge: 1.00 calls, 2011 / 766 tokens in / out per promise per repeat; 297 s per repeat; USD 0.99 in all, 1.32 per 1,000 judgements
- planner, on top of the judge: USD 0.00 per 1,000 promises (retrieval runs once per promise)

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| promise_window | 0.00 | 0 / 0 | 0.000 | 0.000 | {'hop0': 250} |

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
