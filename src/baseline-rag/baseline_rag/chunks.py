"""Passage store for the hybrid baseline: chunks + their embeddings, cached on disk.

Why chunks come from the parsed statement table rather than the PDFs again: the graph arm retrieves
from exactly those statements, so building passages from the same text keeps RQ1 about the retrieval
strategy instead of about two different parses.

Unlike the graph arm, nothing is dropped: tables and metric rows are part of the knowledge base and
are exactly what a question about numbers needs. Each chunk records `prose_ratio`, the share of its
words that pass `looks_like_sentence`, so a table-heavy subset can be ablated in or out.

The build writes three files under `artifacts/baseline/<build_id>/`:

- `chunks.jsonl`    one passage per line with company / year / page / statement ids
- `embeddings.npy`  float32, L2-normalised, row i is chunk i
- `manifest.json`   counts, embedding model, and a hash over the chunk texts

Those three files are the shared knowledge base: a teammate copies the directory (or re-imports it
into Postgres later) and retrieves over byte-identical passages without re-embedding anything.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from gw_common.llm import LLMClient
from gw_common.text import looks_like_sentence

REPO_ROOT = Path(__file__).resolve().parents[3]
STORE_ROOT = REPO_ROOT / "artifacts" / "baseline"
GRAPH_DB = REPO_ROOT / "artifacts" / "graph" / "dev" / "graph.duckdb"
TARGET_WORDS = 200          # course brief suggests 200-400 word passages
OVERLAP_SENTENCES = 1       # one sentence of overlap keeps a split claim readable on both sides
EMBED_BATCH = 128


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    text: str
    company: str
    year: int
    page: int | None
    file: str
    statement_ids: list[str]
    prose_ratio: float = 1.0        # share of words from sentences that pass the prose filter

    @property
    def is_prose(self) -> bool:
        return self.prose_ratio >= 0.6

    def indexed_text(self) -> str:
        """Contextual header, as discussed in the course: metadata helps both BM25 and the encoder."""
        return f"{self.company} ({self.year}), page {self.page}: {self.text}"


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


UNITS = ("passage", "sentence")


def build_chunks(db_path: Path | None = None, unit: str = "passage") -> list[Chunk]:
    """`passage`: ~TARGET_WORDS-word windows over every statement. `sentence`: one chunk per prose
    statement, the same unit and the same prose filter the graph arm retrieves over, so the two can be
    compared with retrieval granularity held fixed."""
    if unit not in UNITS:
        raise ValueError(f"unit must be one of {UNITS}")
    rows = _statements(db_path or GRAPH_DB)
    if unit == "sentence":
        return [
            Chunk(chunk_id=stmt_id, text=text, company=company, year=year, page=page, file=sha,
                  statement_ids=[stmt_id], prose_ratio=1.0)
            for sha, company, year, page, _idx, stmt_id, text in rows
            if text and looks_like_sentence(text)
        ]
    chunks: list[Chunk] = []
    current: list[tuple] = []          # (stmt_id, text, page, is_prose)
    key: tuple | None = None

    def flush() -> None:
        nonlocal current
        if not current or key is None:
            current = []
            return
        sha, company, year = key
        text = " ".join(t for _, t, _, _ in current)
        words = sum(len(t.split()) for _, t, _, _ in current) or 1
        prose_words = sum(len(t.split()) for _, t, _, ok in current if ok)
        chunks.append(Chunk(
            chunk_id=f"{sha[:8]}c{len(chunks):05d}",
            text=text, company=company, year=year, page=current[0][2], file=sha,
            statement_ids=[s for s, _, _, _ in current], prose_ratio=round(prose_words / words, 3),
        ))
        current = current[-OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else []

    for sha, company, year, page, _idx, stmt_id, text in rows:
        if not text or not text.strip():
            continue
        if key != (sha, company, year):
            flush()          # close the previous report before switching
            current = []     # no overlap across reports
            key = (sha, company, year)
        current.append((stmt_id, text, page, looks_like_sentence(text)))
        if sum(len(t.split()) for _, t, _, _ in current) >= TARGET_WORDS:
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


def build(build_id: str = "dev", db_path: Path | None = None, store_root: Path | None = None,
          unit: str = "passage") -> dict:
    chunks = build_chunks(db_path, unit)
    if not chunks:
        raise ValueError("no chunks built: is the graph DuckDB present?")
    client = LLMClient()
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
        "prose_chunks": sum(c.is_prose for c in chunks),
        "target_words": TARGET_WORDS,
        "overlap_sentences": OVERLAP_SENTENCES,
        "embed_model": client.settings.embed_model,
        "dim": int(vectors.shape[1]),
        "chunks_sha256": digest,
        "source_db": str(db_path or GRAPH_DB),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load(build_id: str = "dev", store_root: Path | None = None) -> tuple[list[Chunk], np.ndarray, dict]:
    out_dir = (store_root or STORE_ROOT) / build_id
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"no chunk store at {out_dir}. Build it with `gw-baseline build`, or copy the directory "
            "from a teammate so every experiment retrieves over the same passages."
        )
    chunks = [Chunk(**json.loads(line))
              for line in (out_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    vectors = np.load(out_dir / "embeddings.npy")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(chunks) != vectors.shape[0]:
        raise ValueError(f"chunk/embedding mismatch in {out_dir}: {len(chunks)} vs {vectors.shape[0]}")
    return chunks, vectors, manifest
