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

## 4. Queued: Postgres + pgvector in Docker Compose

To be done **after** the current round of experiments, so the numbers in flight stay on one store.

- `docker compose up` brings up one service, Postgres with pgvector (ParadeDB's image also gives a
  real BM25 index in SQL; otherwise BM25 stays in Python and Postgres serves the vectors).
- Schema: `chunks(chunk_id pk, company, year, page, file, statement_ids text[], text, embedding
  vector(1536))`, btree on `(company, year)` for the condition filters, HNSW on `embedding`.
- Seeding without re-embedding: `gw-baseline export-sql` writes a `COPY`-ready dump from the same
  `chunks.jsonl` + `embeddings.npy`, so a new developer runs compose up, loads the dump and is on the
  identical KB; `pg_dump` of the loaded database is the artefact we share.
- The retriever keeps its current interface: only the candidate-fetch step changes, so the ablation
  and every recorded run stay comparable.
- Course constraint to respect: retrieval must stay our own pipeline. pgvector for ANN and a real
  BM25 index are fine; `LIKE` queries are not.

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
