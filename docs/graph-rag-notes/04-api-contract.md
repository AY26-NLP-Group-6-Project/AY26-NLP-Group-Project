# 04 · API contract (FastAPI)

One app, one router per system, so the front end can switch systems with a query parameter and the
demo can show baseline vs graph side by side.

```
GET  /healthz      -> {status, git_sha, systems: [...], graph_build_id}
GET  /systems      -> [{name, capabilities: {retrieve, classify, trajectory}}]

POST /classify     body {text, company?, year?, aspect?, condition, system}
                   resp {label, scores, evidence: [EvidenceSpan], latency_ms}

POST /retrieve     body {query, company?, year_from?, year_to?, k, condition, system}
                   resp {hits: [EvidenceSpan], latency_ms}

GET  /trajectory   ?company=&aspect=&from=&to=&system=
                   resp {points: [{year, label, statement_id, page, metric?}],
                         transitions: [{from_year, to_year, kind}]}

GET  /graph/subgraph  ?company=&aspect=&hops=2        (graph-rag only)
                   resp {nodes: [...], edges: [...]}   # for the UI graph view

GET  /runs         -> eval runs with their metrics, for the results page
```

Shapes:

- `EvidenceSpan = {statement_id, text, company, year, page, file, score, why}` where `why` says how
  the system found it (`bm25`, `dense`, `rrf`, `graph:follows_up`, `graph:metric`). The UI shows it,
  and it is what makes the graph arm legible in the demo.
- All request and response models are the pydantic models from `gw_common.schemas`. The API never
  defines its own schema.

Rules:

- The API is a thin adapter over the same Protocols the harness uses. No logic lives in routes.
- `condition` takes exactly the five `rq1` values, so any demo query can be reproduced in eval.
- Per-request timeout comes from config (default 8 s) and is enforced by the route, not the system.
- CORS is open in dev only; the front end is served separately.
- Page-cited evidence is mandatory in every response that shows text: `{company, year, page}` must
  be present, because the product claim is provenance, not fluency.
