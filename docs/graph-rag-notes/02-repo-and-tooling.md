# 02 · Repo layout and tooling

## 1. uv workspace

One workspace at the repo root, one member per system, so each system pins its own heavy deps
(a graph store, a vector index, a VLM) without forcing them on everyone.

```
pyproject.toml            # [tool.uv.workspace] members = ["src/common", "src/*-rag"]
uv.lock                   # committed
.python-version           # 3.12
src/
  common/                 # package: gw_common   — shared, dependency-light
    pyproject.toml
    gw_common/
      schemas.py          # pydantic models: Statement, EvidenceSpan, Prediction, Trajectory …
      interfaces.py       # Protocols every system implements (see 03-eval-contract.md)
      registry.py         # entry-point discovery of systems
      datasets.py         # frozen eval snapshots + label_source switch
      eval/
        runner.py         # orchestration, seeds, run manifest
        metrics.py        # classification / retrieval / trajectory / latency metrics
        report.py         # markdown + json results
      api/
        app.py            # FastAPI factory; mounts each system's router
        routes.py         # shared route shapes (see 04-api-contract.md)
  baseline-rag/           # package: baseline_rag — BM25 + dense + RRF + reranker
    pyproject.toml
  graph-rag/              # package: graph_rag   — this line of work
    pyproject.toml
    graph_rag/
      build/              # parse, aspects, canonicalise, measures, derive
      store/              # GraphStore protocol, duckdb_store.py, (neo4j_store.py)
      retrieve.py         # Retriever implementation (traversal)
      trajectory.py       # TrajectoryBuilder implementation
      agent.py            # bounded traversal policy; registered as its own system (M7)
      api.py              # APIRouter contributed to the shared app
artifacts/                # git-ignored: graph builds, indexes, run outputs
data/eval/                # git-ignored: frozen eval snapshots (jsonl + build hash)
```

Note on the directory name: Python cannot import a hyphen, so the *directory* is `src/graph-rag/`
(as agreed) while the *package* inside it is `graph_rag`. uv workspace members may be hyphenated;
imports stay `from graph_rag import ...`.

## 2. Commands

```bash
uv sync                                   # create .venv from uv.lock, all workspace members
uv run gw-eval --list                     # registered systems
uv run gw-data build gw1000 --labels llm_pre                # freeze an eval snapshot (hash in filename)
uv run gw-graph build --config configs/graph.dev.yaml       # M1–M3 pipeline stages
uv run gw-eval --system graph-rag --task rq1 --labels llm_pre
uv run gw-eval --system baseline-rag --task rq1 --labels llm_pre
uv run gw-eval --system agentic-graph-rag --task rq1 --labels llm_pre
uv run gw-eval --compare artifacts/runs/<a> artifacts/runs/<b>
uv run gw-serve --systems graph-rag,baseline-rag --port 8000
```

Console scripts live in `src/common` (`gw-eval`, `gw-serve`) and `src/graph-rag` (`gw-graph`).

## 3. Config and determinism

- Config is YAML under `configs/`, loaded into pydantic settings; every run writes the resolved
  config into its run directory.
- Every run manifest records: git sha, dirty flag, config hash, dataset snapshot hash,
  graph `build_id`, model names/revisions, seed, wall-clock, and (if an LLM is called) token counts.
- Seeds are set for numpy/torch/random; retrieval and clustering must be reproducible.
- No network calls at eval time except to a locally configured model server; anything remote must be
  cached in `artifacts/cache/` keyed by request hash so a re-run is offline.

## 3b. Models and secrets

All model calls go through `gw_common.llm.LLMClient`, configured from a git-ignored `.env`
(template: `.env.example`). Chat and embeddings are configured separately: `LLM_API_KEY`,
`LLM_BASE_URL`, `LLM_MODEL` and `EMB_API_KEY`, `EMB_BASE_URL`, `EMB_MODEL`, each falling back to
`OPENAI_API_KEY` / `OPENAI_BASE_URL`; optional `GW_LLM_TEMPERATURE` (default 0), `GW_LLM_CACHE`,
`GW_EMBED_BACKEND` (`openai` | `fastembed`). If a model rejects the temperature setting, the client
retries without it and records `temperature_applied=False` in the result. Every request/response is cached in
`artifacts/cache/llm.sqlite` keyed by the full payload hash, so an evaluation re-run makes no network
call; each call reports input/output tokens, latency and cache hits for the `ops` metrics. The key is
never written to manifests (`LLMSettings.describe()`).

Canonicalisation embeds with the OpenAI model when a key is configured and with local
`BAAI/bge-small-en-v1.5` (fastembed, ONNX) otherwise. The annotation pools were built with the local
model on purpose, so the gold clustering is not shaped by the embedding model being evaluated.

## 4. Conventions

- Python 3.12, `ruff` + `ruff format`, line length 110 (matches the annotation scripts).
- Type hints on public functions; Protocols rather than base classes (no inheritance across systems).
- No system imports another system. Shared behaviour goes to `gw_common`, or it is duplicated.
- Data files never enter git: `kb/`, `artifacts/`, `data/` stay ignored; only code, configs and docs.
