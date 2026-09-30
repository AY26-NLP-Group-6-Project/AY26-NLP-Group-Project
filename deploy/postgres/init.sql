-- Schema for the shared chunk store. Runs once, when the data volume is first created.
-- Re-running `gw-baseline pg-import` truncates and reloads a build; it never re-embeds.
CREATE EXTENSION IF NOT EXISTS vector;

-- One row per passage of one build. `build_id` lets the passage store (`dev`) and the sentence-unit
-- ablation store (`dev-sent`) coexist; retrieval always filters on it.
CREATE TABLE IF NOT EXISTS chunks (
    build_id       TEXT        NOT NULL,
    chunk_id       TEXT        NOT NULL,
    company        TEXT        NOT NULL,
    year           INTEGER     NOT NULL,
    page           INTEGER,
    file           TEXT        NOT NULL,      -- sha256 of the source report
    statement_ids  TEXT[]      NOT NULL,
    prose_ratio    REAL        NOT NULL DEFAULT 1.0,
    text           TEXT        NOT NULL,
    embedding      vector(1536) NOT NULL,     -- text-embedding-3-small, L2-normalised
    PRIMARY KEY (build_id, chunk_id)
);

-- Condition filters are always company + year; the ANN index serves the dense stage.
CREATE INDEX IF NOT EXISTS chunks_company_year ON chunks (build_id, company, year);
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- The manifest of each loaded build, so a client can verify it is talking to the same KB as the files.
CREATE TABLE IF NOT EXISTS kb_manifest (
    build_id   TEXT PRIMARY KEY,
    manifest   JSONB NOT NULL,
    loaded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
