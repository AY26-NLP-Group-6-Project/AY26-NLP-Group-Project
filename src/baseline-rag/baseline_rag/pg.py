"""Postgres + pgvector as the shared home of the chunk store.

The files under `artifacts/baseline/<build_id>/` stay the source of truth (they are what gets packaged
and handed around). This module loads them into Postgres without re-embedding, verifies a database
against the files, and serves dense candidates from pgvector so a teammate with only the database can
retrieve over the identical passages.

    docker compose up -d
    uv run gw-baseline pg-import --build-id dev
    uv run gw-baseline pg-check  --build-id dev
    GW_BASELINE_BACKEND=postgres uv run gw-eval --system baseline-rag ...

Vectors travel as pgvector's text literal (`[0.1,0.2,...]`), so no extra client library is needed.
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from baseline_rag import chunks as chunk_store
from baseline_rag.chunks import Chunk

DEFAULT_DSN = "postgresql://gw:gw@localhost:5432/gw"
COPY_BATCH = 500


def dsn() -> str:
    return os.getenv("PG_DSN", DEFAULT_DSN)


def _connect(conn_str: str | None = None):
    import psycopg

    return psycopg.connect(conn_str or dsn())


def _vector_literal(row: np.ndarray) -> str:
    return "[" + ",".join(f"{x:.7g}" for x in row.tolist()) + "]"


def import_store(build_id: str = "dev", conn_str: str | None = None) -> dict:
    """Truncate the build's rows and COPY the files in. Idempotent; never touches other builds."""
    chunks, vectors, manifest = chunk_store.load(build_id)
    with _connect(conn_str) as con, con.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE build_id = %s", (build_id,))
        with cur.copy(
            "COPY chunks (build_id, chunk_id, company, year, page, file, statement_ids, prose_ratio, "
            "text, embedding) FROM STDIN"
        ) as copy:
            for c, vec in zip(chunks, vectors, strict=True):
                copy.write_row((build_id, c.chunk_id, c.company, c.year, c.page, c.file,
                                c.statement_ids, c.prose_ratio, c.text, _vector_literal(vec)))
        cur.execute(
            "INSERT INTO kb_manifest (build_id, manifest, loaded_at) VALUES (%s, %s, now()) "
            "ON CONFLICT (build_id) DO UPDATE SET manifest = EXCLUDED.manifest, loaded_at = now()",
            (build_id, json.dumps(manifest)),
        )
        con.commit()
    return {"build_id": build_id, "rows": len(chunks), "chunks_sha256": manifest["chunks_sha256"]}


def check(build_id: str = "dev", conn_str: str | None = None) -> dict:
    """Does the database hold the same build as the files? Row count and text hash must both match."""
    _, _, manifest = chunk_store.load(build_id)
    with _connect(conn_str) as con, con.cursor() as cur:
        cur.execute("SELECT count(*) FROM chunks WHERE build_id = %s", (build_id,))
        rows = cur.fetchone()[0]
        cur.execute("SELECT manifest FROM kb_manifest WHERE build_id = %s", (build_id,))
        loaded = cur.fetchone()
        cur.execute("SELECT text FROM chunks WHERE build_id = %s ORDER BY chunk_id", (build_id,))
        digest = hashlib.sha256("\n".join(t for (t,) in cur.fetchall()).encode("utf-8")).hexdigest()[:12]
    files_digest = hashlib.sha256(
        "\n".join(c.text for c in sorted(chunk_store.load(build_id)[0], key=lambda c: c.chunk_id))
        .encode("utf-8")
    ).hexdigest()[:12]
    return {
        "build_id": build_id,
        "rows_db": rows, "rows_files": manifest["chunks"],
        "manifest_loaded": bool(loaded),
        "text_hash_db": digest, "text_hash_files": files_digest,
        "ok": rows == manifest["chunks"] and digest == files_digest and bool(loaded),
    }


class PgChunkSource:
    """Chunks and dense candidates straight from Postgres; BM25 stays in-process over the same rows."""

    def __init__(self, build_id: str = "dev", conn_str: str | None = None) -> None:
        self.build_id = build_id
        self.conn_str = conn_str or dsn()
        self.con = _connect(self.conn_str)
        with self.con.cursor() as cur:
            cur.execute("SELECT manifest FROM kb_manifest WHERE build_id = %s", (build_id,))
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"build {build_id!r} is not loaded; run `gw-baseline pg-import`")
            self.manifest = row[0]
            cur.execute(
                "SELECT chunk_id, text, company, year, page, file, statement_ids, prose_ratio "
                "FROM chunks WHERE build_id = %s ORDER BY chunk_id", (build_id,)
            )
            self.chunks = [Chunk(chunk_id=r[0], text=r[1], company=r[2], year=r[3], page=r[4], file=r[5],
                                 statement_ids=list(r[6]), prose_ratio=r[7]) for r in cur.fetchall()]
        self._index = {c.chunk_id: i for i, c in enumerate(self.chunks)}

    def dense_search(self, query_vector, allowed_ids: set[int] | None, k: int) -> list[tuple[int, float]]:
        """Top-k by cosine distance inside the allowed set (resolved to company/year filters)."""
        literal = _vector_literal(np.asarray(query_vector, dtype=np.float32))
        params: list = [self.build_id]
        where = "build_id = %s"
        if allowed_ids is not None:
            if not allowed_ids:
                return []
            ids = [self.chunks[i].chunk_id for i in allowed_ids]
            where += " AND chunk_id = ANY(%s)"
            params.append(ids)
        with self.con.cursor() as cur:
            cur.execute(
                f"SELECT chunk_id, 1 - (embedding <=> %s::vector) AS score FROM chunks WHERE {where} "
                f"ORDER BY embedding <=> %s::vector LIMIT %s",
                [literal, *params, literal, k],
            )
            return [(self._index[cid], float(score)) for cid, score in cur.fetchall()]


def package(build_id: str = "dev", out: Path | None = None) -> dict:
    """Zip the store for distribution: the three files, a checksum list and a README with the import
    steps. Derived passages and metadata only, never the source PDFs."""
    src = chunk_store.STORE_ROOT / build_id
    chunks, _, manifest = chunk_store.load(build_id)
    out = out or (chunk_store.REPO_ROOT / "dist" / f"gw-kb-{build_id}-{manifest['chunks_sha256']}.zip")
    out.parent.mkdir(parents=True, exist_ok=True)
    files = ["chunks.jsonl", "embeddings.npy", "manifest.json"]
    sums = {f: hashlib.sha256((src / f).read_bytes()).hexdigest() for f in files}
    readme = _package_readme(build_id, manifest, sums)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in files:
            zf.write(src / f, arcname=f"{build_id}/{f}")
        zf.writestr(f"{build_id}/SHA256SUMS", "".join(f"{h}  {f}\n" for f, h in sums.items()))
        zf.writestr(f"{build_id}/README.md", readme)
    return {"out": str(out), "bytes": out.stat().st_size, "chunks": len(chunks),
            "chunks_sha256": manifest["chunks_sha256"], "files": sums}


def _package_readme(build_id: str, manifest: dict, sums: dict[str, str]) -> str:
    passages = (f"{manifest['chunks']:,} ({manifest.get('unit', 'passage')} unit, "
                f"target {manifest['target_words']} words)")
    return f"""# Greenwash-RAG knowledge base · build `{build_id}`

Packaged {datetime.now(UTC):%Y-%m-%d %H:%M} UTC. **Academic use only (AI6127 group project).** These are
derived passages and metadata from SGX-listed companies' public sustainability reports; the reports
themselves remain the issuers' copyright and are not included. Do not publish or redistribute.

| | |
|---|---|
| passages | {passages} |
| companies / reports | {manifest['companies']} / {manifest['reports']} |
| words | {manifest['words']:,} |
| embedding | `{manifest['embed_model']}`, {manifest['dim']} dims, L2-normalised, float32 |
| content hash | `{manifest['chunks_sha256']}` (over the passage texts; every run manifest records it) |

## Files

- `chunks.jsonl` — one passage per line: `chunk_id, text, company, year, page, file (report sha256),
  statement_ids, prose_ratio`
- `embeddings.npy` — row *i* is the vector of line *i* of `chunks.jsonl`
- `manifest.json` — the table above, machine-readable
- `SHA256SUMS` — verify with `sha256sum -c SHA256SUMS`

## Use it

**Option A, files only (no database):** unzip so the folder sits at `artifacts/baseline/{build_id}/`
inside the repo. `gw-baseline stats --build-id {build_id}` should print hash `{manifest['chunks_sha256']}`.
Every `gw-eval --system baseline-rag` run then retrieves over these exact passages.

**Option B, shared Postgres + pgvector:**

```bash
docker compose up -d                              # pgvector/pgvector:pg16, schema auto-created
uv run gw-baseline pg-import --build-id {build_id}   # COPY, no re-embedding (~1 min)
uv run gw-baseline pg-check  --build-id {build_id}   # row count and text hash must match
GW_BASELINE_BACKEND=postgres uv run gw-eval --system baseline-rag --split dev --repeats 3
```

Connection string: `postgresql://gw:gw@localhost:5432/gw` (override with `PG_DSN`).

## Reading it from anything else

```python
import json, numpy as np
chunks = [json.loads(l) for l in open("chunks.jsonl", encoding="utf-8")]
vectors = np.load("embeddings.npy")           # shape ({manifest['chunks']}, {manifest['dim']})
```

Query vectors must come from the same model (`{manifest['embed_model']}`) and be L2-normalised; cosine
similarity is then a dot product.
"""
