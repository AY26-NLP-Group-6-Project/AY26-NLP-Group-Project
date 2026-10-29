# The hybrid baseline and the knowledge-base stores

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
company and year filters come from the condition. Passages are indexed with a contextual header
(`Company (Year), page N: …`), which helps both BM25 and the encoder.

## 2. The stores

Chunks are built from the parsed statement table the graph retrieves from, not from the PDFs again: if
two arms read different parses, the comparison measures the parser. Three stores exist, keyed by
`build_id` (`GW_BASELINE_BUILD`):

| store | unit | chunks | hash | built with |
|---|---|---|---|---|
| `dev` | passages of about 200 words, one sentence of overlap, never crossing a report; tables and page furniture kept and marked by `prose_ratio` | 18,839 | `c80d0ab23191` | `gw-baseline build` |
| `dev-sent` | one chunk per statement that passes the prose filter (`gw_common.text.looks_like_sentence`), the set the graph arms retrieve over | 71,342 | `b1c181dcaf1a` | `gw-baseline build --build-id dev-sent --unit sentence` |
| `dev-stmt` | one chunk per statement of five words or more, no prose filter | 108,376 | `d8a62bfe40c6` | `gw-baseline build --build-id dev-stmt --unit statement --reuse dev-sent` |

Why three. Passages are the course's unit and the first baseline; sentences hold the retrieval unit
fixed between the baseline and the graph; the all-statement store measures what the prose filter costs
(it drops 34 % of statements, mostly third-person sentences without one of its listed verbs, and
result sentences with figures). `--reuse` copies the vectors of identical chunks from an existing store,
so only the new ones are embedded.

Each store is a directory `artifacts/baseline/<build_id>/` with `chunks.jsonl` (text and
`{company, year, page, file, statement_ids, prose_ratio}`), `embeddings.npy` (float32, L2-normalised)
and `manifest.json` (counts, model, dimension, a hash over the chunk texts). Copy the directory and you
have the same knowledge base; the hash catches drift between machines.

```bash
uv run gw-baseline build [--build-id X --unit passage|sentence|statement --reuse Y]
uv run gw-baseline stats --build-id dev       # counts, words per chunk, embedding shape
uv run gw-baseline sample --build-id dev --n 3
```

The classifier shows at most 800 characters per span; passages need the room, sentences use a fraction.

## 3. Postgres + pgvector

`docker-compose.yml` starts `pgvector/pgvector:pg16`; `deploy/postgres/init.sql` creates
`chunks(build_id, chunk_id, company, year, page, file, statement_ids, prose_ratio, text, embedding
vector(1536))` with a btree on `(build_id, company, year)` for the condition filters and an HNSW cosine
index for the dense stage, plus `kb_manifest` for each loaded build.

```bash
docker compose up -d
uv run gw-baseline pg-import --build-id dev       # COPY from the files, no re-embedding
uv run gw-baseline pg-check  --build-id dev       # row count and text hash must equal the files
GW_BASELINE_BACKEND=postgres uv run gw-eval --system baseline-rag --split dev --repeats 3
```

The files stay the source of truth; the database is a mirror, verified by `pg-check`. With the
Postgres backend the retriever reads text and metadata from the database, rebuilds BM25 in-process
over those rows and takes dense candidates from pgvector; on dev queries the two backends returned the
same top-5 lists. Retrieval is still our pipeline; Postgres serves vectors and metadata.

## 4. Distributing the store

`uv run gw-baseline package --build-id <store> [--with-eval]` writes `dist/gw-kb-<store>-<hash>.zip`:
the three store files, `SHA256SUMS`, a README with both import paths and what the unit is, and
optionally the frozen evaluation snapshot. One archive per store: `dev` about 100 MB, `dev-sent` about
370 MB, `dev-stmt` about 560 MB (float32 vectors compress little). Teammates comparing against the
reference baseline need `dev-sent`. Derived text and metadata only; the PDFs are never included. `dist/`
is git-ignored; the archives travel through a channel the group controls.
