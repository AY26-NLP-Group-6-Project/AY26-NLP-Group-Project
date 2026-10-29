"""The knowledge base: every statement of the parsed reports, as chunks with their embeddings.

Chunks come from the parsed statement table the graph retrieves from, not from the PDFs again: if two
arms read different parses, the comparison measures the parser. Nothing is filtered by shape. Tables,
metric rows and result lines are part of the knowledge base, and a question about numbers or about what
became of a target needs exactly those rows.

Two units. `statement` (the default) is one chunk per statement of at least `MIN_STATEMENT_WORDS`
words, the unit every arm retrieves over. `passage` is a window of about `TARGET_WORDS` words over the
same statements, one sentence of overlap, never crossing a report: the course's unit, kept as an
ablation of retrieval granularity.

The build writes three files under `artifacts/baseline/<build_id>/`:

- `chunks.jsonl`    one chunk per line with company / year / page / statement ids
- `embeddings.npy`  float32, L2-normalised, row i is chunk i
- `manifest.json`   counts, embedding model, and a hash over the chunk texts

Those three files are the shared knowledge base: a teammate copies the directory (or imports it into
Postgres) and retrieves over byte-identical chunks without re-embedding anything.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import numpy as np
from gw_common.llm import LLMClient
from gw_common.text import MIN_STATEMENT_WORDS, is_statement

REPO_ROOT = Path(__file__).resolve().parents[3]
STORE_ROOT = REPO_ROOT / "artifacts" / "baseline"
GRAPH_DB = REPO_ROOT / "artifacts" / "graph" / "dev" / "graph.duckdb"
DEFAULT_BUILD = "statements"
UNITS = ("statement", "passage")
TARGET_WORDS = 200          # course brief suggests 200-400 word passages
OVERLAP_SENTENCES = 1       # one sentence of overlap keeps a split claim readable on both sides
EMBED_BATCH = 128

__all__ = ["Chunk", "DEFAULT_BUILD", "MIN_STATEMENT_WORDS", "UNITS", "build", "build_chunks", "load"]


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    text: str
    company: str
    year: int
    page: int | None
    file: str
    statement_ids: list[str]

    def indexed_text(self) -> str:
        """Contextual header, as discussed in the course: metadata helps both BM25 and the encoder."""
        return f"{self.company} ({self.year}), page {self.page}: {self.text}"


_FIELDS = {f.name for f in fields(Chunk)}


def _statements(db_path: Path) -> list[tuple]:
    import duckdb

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return con.execute(
            "SELECT sha256, company, year, page, idx, stmt_id, text FROM statements "
            "ORDER BY sha256, page, idx"
        ).fetchall()
    finally:
        con.close()


def build_chunks(db_path: Path | None = None, unit: str = "statement") -> list[Chunk]:
    """`statement`: one chunk per statement of at least MIN_STATEMENT_WORDS words. `passage`: windows of
    about TARGET_WORDS words over every statement, one sentence of overlap, never crossing a report."""
    if unit not in UNITS:
        raise ValueError(f"unit must be one of {UNITS}")
    rows = _statements(db_path or GRAPH_DB)
    if unit == "statement":
        return [
            Chunk(chunk_id=stmt_id, text=text, company=company, year=year, page=page, file=sha,
                  statement_ids=[stmt_id])
            for sha, company, year, page, _idx, stmt_id, text in rows
            if text and is_statement(text)
        ]
    chunks: list[Chunk] = []
    current: list[tuple] = []          # (stmt_id, text, page)
    key: tuple | None = None

    def flush() -> None:
        nonlocal current
        if not current or key is None:
            current = []
            return
        sha, company, year = key
        chunks.append(Chunk(
            chunk_id=f"{sha[:8]}c{len(chunks):05d}",
            text=" ".join(t for _, t, _ in current), company=company, year=year, page=current[0][2],
            file=sha, statement_ids=[s for s, _, _ in current],
        ))
        current = current[-OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else []

    for sha, company, year, page, _idx, stmt_id, text in rows:
        if not text or not text.strip():
            continue
        if key != (sha, company, year):
            flush()          # close the previous report before switching
            current = []     # no overlap across reports
            key = (sha, company, year)
        current.append((stmt_id, text, page))
        if sum(len(t.split()) for _, t, _ in current) >= TARGET_WORDS:
            flush()
    flush()
    return chunks


def embed_chunks(chunks: list[Chunk], client: LLMClient | None = None) -> np.ndarray:
    client = client or LLMClient()
    vectors: list[np.ndarray] = []
    for start in range(0, len(chunks), EMBED_BATCH):
        batch = [c.indexed_text() for c in chunks[start:start + EMBED_BATCH]]
        vectors.append(np.asarray(client.embed(batch), dtype=np.float32))
        print(f"  embedded {min(start + EMBED_BATCH, len(chunks))}/{len(chunks)}", flush=True)
    return np.vstack(vectors)


def build(build_id: str = DEFAULT_BUILD, db_path: Path | None = None, store_root: Path | None = None,
          unit: str = "statement", reuse: str | None = None) -> dict:
    """`reuse` names a store built from the same statements: a chunk with the same id and text takes its
    vector from there, so only the chunks that store lacks are embedded."""
    chunks = build_chunks(db_path, unit)
    if not chunks:
        raise ValueError("no chunks built: is the graph DuckDB present?")
    client = LLMClient()
    reused = 0
    if reuse:
        old_chunks, old_vectors, old_manifest = load(reuse, store_root)
        if old_manifest["embed_model"] != client.settings.embed_model:
            raise ValueError(f"{reuse} was embedded with {old_manifest['embed_model']}")
        row_of = {(c.chunk_id, c.text): i for i, c in enumerate(old_chunks)}
        rows = [row_of.get((c.chunk_id, c.text)) for c in chunks]
        fresh = [c for c, row in zip(chunks, rows, strict=True) if row is None]
        new_vectors = embed_chunks(fresh, client) if fresh else np.zeros((0, old_vectors.shape[1]))
        vectors = np.zeros((len(chunks), old_vectors.shape[1]), dtype=np.float32)
        at = 0
        for i, row in enumerate(rows):
            if row is None:
                vectors[i], at = new_vectors[at], at + 1
            else:
                vectors[i], reused = old_vectors[row], reused + 1
    else:
        vectors = embed_chunks(chunks, client)
    out_dir = (store_root or STORE_ROOT) / build_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    np.save(out_dir / "embeddings.npy", vectors)
    digest = hashlib.sha256("\n".join(c.text for c in chunks).encode("utf-8")).hexdigest()[:12]
    manifest = {
        "build_id": build_id,
        "unit": unit,
        "chunks": len(chunks),
        "companies": len({c.company for c in chunks}),
        "reports": len({c.file for c in chunks}),
        "words": sum(len(c.text.split()) for c in chunks),
        "min_statement_words": MIN_STATEMENT_WORDS,
        "target_words": TARGET_WORDS,
        "overlap_sentences": OVERLAP_SENTENCES,
        "embed_model": client.settings.embed_model,
        "dim": int(vectors.shape[1]),
        "chunks_sha256": digest,
        "source_db": str(db_path or GRAPH_DB),
    }
    if reuse:
        manifest["vectors_reused"] = {"from": reuse, "chunks": reused}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load(build_id: str = DEFAULT_BUILD,
         store_root: Path | None = None) -> tuple[list[Chunk], np.ndarray, dict]:
    out_dir = (store_root or STORE_ROOT) / build_id
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"no chunk store at {out_dir}. Build it with `gw-baseline build`, or copy the directory "
            "from a teammate so every experiment retrieves over the same chunks."
        )
    chunks = []
    for line in (out_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines():
        if line:
            record = json.loads(line)
            chunks.append(Chunk(**{k: v for k, v in record.items() if k in _FIELDS}))
    vectors = np.load(out_dir / "embeddings.npy")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(chunks) != vectors.shape[0]:
        raise ValueError(f"chunk/embedding mismatch in {out_dir}: {len(chunks)} vs {vectors.shape[0]}")
    return chunks, vectors, manifest
