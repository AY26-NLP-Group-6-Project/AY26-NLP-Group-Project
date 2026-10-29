# The hybrid baseline and the knowledge base

The baseline exists so every other arm has something honest to beat: "does a graph help?" only means
something next to ordinary RAG built on the same text, scored by the same classifier, under the same
evidence budget. Its results are in `results.md`; its runs under `results/baseline/`.

## 1. The retriever

`src/baseline-rag` (`gw-eval --system baseline-rag`), stages in `baseline_rag/index.py`:

| stage | choice | why |
|---|---|---|
| sparse | Okapi BM25, k1 1.5, b 0.75, own inverted index | course requirement; no SQL `LIKE` shortcut |
| dense | `text-embedding-3-small`, cosine over L2-normalised vectors | one embedding model for the whole project |
| fusion | reciprocal rank fusion, k0 = 60, top 50 from each retriever | scale-free, the usual default |
| rerank | `Xenova/ms-marco-MiniLM-L-6-v2` cross-encoder over the top 20, via fastembed (ONNX, CPU) | no torch, loads once per process |

`GW_BASELINE_MODE` selects `bm25` / `dense` / `rrf` / `rrf+rerank`, so a retrieval ablation runs
through one code path. Conditions: `sentence_only`, `local`, `same_report_rrf`, `cross_year_rrf`; the
company and year filters come from the condition. Chunks are indexed with a contextual header
(`Company (Year), page N: …`), which helps both BM25 and the encoder.

## 2. The knowledge base

Chunks are built from the parsed statement table the graph retrieves from, not from the PDFs again: if
two arms read different parses, the comparison measures the parser. Every statement of five words or
more is a chunk: prose, table rows and metric lines alike. Nothing is filtered by shape; the shorter
fragments are headers, page numbers and lone table cells. A question about numbers, or about what
became of a target, needs exactly the rows a prose filter would drop. Two stores, keyed by `build_id`
(`GW_BASELINE_BUILD`):

| store | unit | chunks | hash | built with |
|---|---|---|---|---|
| `statements` (default) | one chunk per statement of five words or more | 108,376 | `d8a62bfe40c6` | `gw-baseline build` |
| `passages` | windows of about 200 words over the same statements, one sentence of overlap, never crossing a report | 18,839 | `c80d0ab23191` | `gw-baseline build --build-id passages --unit passage` |

Why two. The statement is the unit every arm retrieves over: the graph's edges point at statements, so
a baseline that retrieves over the same statements keeps RQ1 about the retrieval strategy and not about
granularity. The passage store is the course's unit, kept as the granularity ablation (`results.md`).
`--reuse <store>` copies the vectors of identical chunks from an existing store, so only new chunks are
embedded.

Each store is a directory `artifacts/baseline/<build_id>/` with `chunks.jsonl` (text and
`{company, year, page, file, statement_ids}`), `embeddings.npy` (float32, L2-normalised) and
`manifest.json` (counts, model, dimension, a hash over the chunk texts). Copy the directory and you have
the same knowledge base; the hash catches drift between machines.

```bash
uv run gw-baseline build [--build-id X --unit statement|passage --reuse Y]
uv run gw-baseline stats                      # counts, words per chunk, embedding shape
uv run gw-baseline sample --n 3
```

The classifier shows at most 800 characters per span; passages need the room, statements use a fraction.

## 3. Postgres + pgvector

`docker-compose.yml` starts `pgvector/pgvector:pg16`; `deploy/postgres/init.sql` creates
`chunks(build_id, chunk_id, company, year, page, file, statement_ids, text, embedding vector(1536))`
with a btree on `(build_id, company, year)` for the condition filters and an HNSW cosine index for the
dense stage, plus `kb_manifest` for each loaded build.

```bash
docker compose up -d
uv run gw-baseline pg-import       # COPY from the files, no re-embedding
uv run gw-baseline pg-check        # row count and text hash must equal the files
GW_BASELINE_BACKEND=postgres uv run gw-eval --system baseline-rag --split dev --repeats 3
```

The files stay the source of truth; the database is a mirror, verified by `pg-check`. With the
Postgres backend the retriever reads text and metadata from the database, rebuilds BM25 in-process
over those rows and takes dense candidates from pgvector; on dev queries the two backends returned the
same top-5 lists. Retrieval is still our pipeline; Postgres serves vectors and metadata.

## 4. Distributing the store

`uv run gw-baseline package [--build-id <store>] [--with-eval]` writes `dist/gw-kb-<store>-<hash>.zip`:
the three store files, `SHA256SUMS`, a README with both import paths and what the unit is, and
optionally the frozen evaluation snapshot. `gw-kb-statements-d8a62bfe40c6.zip` is about 560 MB (float32
vectors compress little) and is the one teammates need; `gw-kb-passages-c80d0ab23191.zip` is about
100 MB. Derived text and metadata only; the PDFs are never included. `dist/` is git-ignored; the
archives travel through a channel the group controls.
