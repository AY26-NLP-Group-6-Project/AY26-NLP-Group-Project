# 20261031T085149Z-agentic-rag-rq2

- system: `agentic-rag` · task: `rq2` · condition: `promise_window`, k = 20
- gold: `rq2promises` @ `a6f35618dd6e` · n = 250 · split: `test` · repeats: 3
- judge: `v2` · prompt `promise_outcome_v2.md` @ `d7592a1f3210` · model: `gpt-5.6-luna` · effort: `low`
- retriever: `{"store": "statements", "chunks_sha256": "d8a62bfe40c6", "unit": "statement", "chunks": 108376, "mode": "rrf", "backend": "files", "corpus": "statements", "max_hops": 0, "timeout_s": 90.0, "select": "verified", "prompts": {"rq1_gate": "05cc23d5a014", "rq1_verify": "704bc413c655", "rq2_plan": "8a60f9ec4134"}, "trace_file": "traces-20261031T165154-10976.jsonl"}`
- git: `bfd27d65` · wall: 928.4s

| accuracy (mean ± sd) | macro-F1 (mean ± sd) | κ | vote accuracy | vote macro-F1 | vote κ | unstable |
|---|---|---|---|---|---|---|
| 0.7600 ±0.004 | 0.6591 ±0.028 | 0.603 | 0.7640 | 0.6840 | 0.610 | 39 |

Bootstrap 95 % CI of the vote: accuracy 0.712–0.816, macro-F1 0.574–0.772.

## What a reader of the system's output can rely on (majority vote)

| | k / n | share |
|---|---|---|
| verdict where the gold is unclear | 17 / 64 | 0.266 |
| unclear where the gold has a verdict | 39 / 186 | 0.210 |
| verdicts that are right | 144 / 164 | 0.878 |

## Per class (majority vote)

| outcome | precision | recall | F1 | gold n | system n |
|---|---|---|---|---|---|
| achieved | 0.928 | 0.800 | 0.859 | 145 | 125 |
| failed | 0.800 | 0.706 | 0.750 | 34 | 30 |
| unclear | 0.547 | 0.734 | 0.627 | 64 | 86 |
| disappeared | 0.444 | 0.571 | 0.500 | 7 | 9 |

Confusion, gold rows → system columns: {"achieved": {"achieved": 116, "failed": 2, "unclear": 27, "disappeared": 0}, "failed": {"achieved": 1, "failed": 24, "unclear": 9, "disappeared": 0}, "unclear": {"achieved": 8, "failed": 4, "unclear": 47, "disappeared": 5}, "disappeared": {"achieved": 0, "failed": 0, "unclear": 3, "disappeared": 4}}

## By label source

| source | n | accuracy | κ |
|---|---|---|---|
| human_pair | 115 | 0.800 | 0.694 |
| model_pair | 135 | 0.733 | 0.515 |

## Evidence, speed and cost

- evidence: coverage 1.00, 11.5 statements per promise from 2.0 report years; by source {"agent:hop0:neighbour": 683, "agent:hop0:retrieved": 2197}
- retrieval: p50 274 ms, p95 412 ms per promise
- judge: 1.00 calls, 2008 / 772 tokens in / out per promise per repeat; 283 s per repeat; USD 1.00 in all, 1.33 per 1,000 judgements
- planner, on top of the judge: USD 0.00 per 1,000 promises (retrieval runs once per promise)

## Agent

| condition | planner calls / item | tokens in / out / item | evidence from later hops | items with no evidence | stop reasons |
|---|---|---|---|---|---|
| promise_window | 0.00 | 0 / 0 | 0.000 | 0.000 | {'hop0': 250} |

Compare two runs with `gw-eval --compare A B`: paired on the same promises, McNemar on the votes.
