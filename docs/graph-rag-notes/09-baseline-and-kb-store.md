# 09 · The hybrid baseline and the shared knowledge-base store

The baseline exists so every other arm has something honest to beat: "does a graph help?" only means
something next to ordinary RAG built on the same passages, scored by the same classifier, under the
same evidence budget.

## 1. What the baseline is

`src/baseline-rag` (`gw-eval --system baseline-rag`), stages in `baseline_rag/index.py`:

| stage | choice | why |
|---|---|---|
| sparse | Okapi BM25, k1 1.5, b 0.75, own inverted index | course requirement; no SQL `LIKE` shortcut |
| dense | `text-embedding-3-small`, cosine over L2-normalised vectors | same embedding model as canonicalisation, one vendor to reason about |
| fusion | RRF, k0 = 60, top-50 from each retriever | scale-free, the usual default |
| rerank | `Xenova/ms-marco-MiniLM-L-6-v2` cross-encoder over the top 20, via fastembed ONNX | CPU-only, no torch, loads once per process |

`GW_BASELINE_MODE` selects `bm25` / `dense` / `rrf` / `rrf+rerank`, so the retrieval ablation runs
through one code path. Conditions: `sentence_only`, `local`, `same_report_rrf`, `cross_year_rrf`;
company and year filters come from the condition, which is also RQ3's question.

## 2. The shared passage store

Chunks are built from the **parsed statement table the graph arm retrieves from**, not from the PDFs
again: if the two arms read different parses, RQ1 would measure the parser. The same prose filter
(`gw_common.text.looks_like_sentence`, moved out of the graph package for exactly this reason)
applies to both.

- ~280-word passages, one sentence of overlap, never crossing a report boundary.
- Each passage carries `{company, year, page, file, statement_ids}` and is indexed with a contextual
  header (`Company (Year), page N: …`).
- `artifacts/baseline/<build_id>/`: `chunks.jsonl`, `embeddings.npy` (float32, L2-normalised),
  `manifest.json` (counts, model, dim, a hash over the chunk texts).

```bash
uv run gw-baseline build          # writes the three files (embeds once)
uv run gw-baseline stats          # counts, words per chunk, embedding shape
uv run gw-baseline sample --n 3   # eyeball the passages
```

**Copy the directory and you have the same knowledge base.** A teammate never re-embeds, and the
manifest hash catches silent drift between machines.

## 3. Evidence budget

The shared classifier shows at most `EVIDENCE_CHARS = 800` per span (was 300). Passage retrievers
need the room; sentence retrievers use a fraction of it. Runs made before this change (sections 4f–4i)
used 300 and must be re-run before being compared with baseline numbers.

## 4. Postgres + pgvector in Docker Compose (done 2026-09-30)

`docker-compose.yml` starts one service, `pgvector/pgvector:pg16`, and `deploy/postgres/init.sql`
creates the schema on first start: `chunks(build_id, chunk_id, company, year, page, file,
statement_ids, prose_ratio, text, embedding vector(1536))` with a btree on `(build_id, company, year)`
for the condition filters and an HNSW cosine index for the dense stage, plus `kb_manifest` holding each
loaded build's manifest.

```bash
docker compose up -d
uv run gw-baseline pg-import --build-id dev    # COPY from the files, ~40 s, no re-embedding
uv run gw-baseline pg-check  --build-id dev    # row count + text hash must equal the files
GW_BASELINE_BACKEND=postgres uv run gw-eval --system baseline-rag --split dev --repeats 3
```

- The files stay the source of truth; the database is a mirror, verified by `pg-check` (18,839 rows,
  hash `c80d0ab23191`). Several builds coexist (`dev`, `dev-sent`), keyed by `build_id`.
- With `GW_BASELINE_BACKEND=postgres` the retriever reads chunk text and metadata from the database,
  rebuilds BM25 in-process over those rows and takes dense candidates from pgvector. On 6 dev queries
  the `files` and `postgres` backends returned identical top-5 lists.
- Course constraint respected: retrieval is still our pipeline (BM25 + embeddings + RRF + rerank);
  Postgres serves vectors and metadata, no `LIKE` search.

### Distribution package

`uv run gw-baseline package --build-id dev` writes `dist/gw-kb-dev-<hash>.zip` (~100 MB): the three
store files, `SHA256SUMS`, and a README with both import paths (files-only, or compose + `pg-import`).
Derived passages and metadata only; the PDFs are never included. `dist/` is git-ignored; the archive is
shared through a channel the group controls, not the repository.

## 5. Open question: passage count vs the course minimum

The brief asks for **≥10,000 passages**. The current store has **6,660** (52 companies, 233 reports,
1.93 M words after the prose filter). Ways to clear it, in order of honesty:

1. Parse the remaining reports: the graph covers eval-set companies only (decision D2), so 7 reports
   and 4 companies of the 240/56 corpus are missing. Small gain (~3 %).
2. Count passages over the unfiltered text as well: the filter removes tables and page furniture that
   are still part of the knowledge base. Report both numbers and say which one retrieval uses.
3. Chunk at 200 words instead of 280: ~9.6k passages, and the brief itself lists 200-word chunks as a
   normal choice. Combined with (1) this clears 10k.

Recommendation: do (1) + (3) and report both the retrieval store and the full corpus counts.
