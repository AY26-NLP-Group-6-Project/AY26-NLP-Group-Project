"""DuckDB-backed graph store (decision D1).

Node and edge tables live in one DuckDB file per build; multi-hop work loads a company-scoped
subgraph into networkx, which stays small because ESG graphs are company-centred and star-shaped
(EmeraldMind section 7.2). Nothing above this module may import duckdb.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import networkx as nx

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    company     VARCHAR PRIMARY KEY,
    sgx_code    VARCHAR
);
CREATE TABLE IF NOT EXISTS reports (
    sha256      VARCHAR PRIMARY KEY,
    company     VARCHAR,
    year        INTEGER,
    file        VARCHAR,
    pages       INTEGER
);
CREATE TABLE IF NOT EXISTS statements (
    stmt_id     VARCHAR PRIMARY KEY,
    sha256      VARCHAR,
    company     VARCHAR,
    year        INTEGER,
    page        INTEGER,
    idx         INTEGER,
    text        VARCHAR,
    norm_text   VARCHAR,
    source      VARCHAR          -- corpus | eval
);
CREATE TABLE IF NOT EXISTS aspects (
    aspect_id   VARCHAR PRIMARY KEY,
    canonical   VARCHAR,
    category    VARCHAR,
    method      VARCHAR          -- gold_span (M1) | cluster (M2) | llm (M3)
);
CREATE TABLE IF NOT EXISTS aspect_aliases (
    surface     VARCHAR,
    aspect_id   VARCHAR,
    method      VARCHAR,
    PRIMARY KEY (surface, aspect_id)
);
CREATE TABLE IF NOT EXISTS mentions (
    stmt_id      VARCHAR,
    aspect_id    VARCHAR,
    action       VARCHAR,        -- implemented | planning | indeterminate | none | NULL (unlabelled)
    label_source VARCHAR,        -- llm_pre | human_majority | NULL
    method       VARCHAR,        -- gold_span | string_match | llm
    PRIMARY KEY (stmt_id, aspect_id)
);
CREATE TABLE IF NOT EXISTS follows_up (
    from_stmt   VARCHAR,
    to_stmt     VARCHAR,
    aspect_id   VARCHAR,
    company     VARCHAR,
    years_apart INTEGER,
    same_text   BOOLEAN,          -- the later statement is the earlier one copied verbatim
    PRIMARY KEY (from_stmt, to_stmt, aspect_id)
);
"""


@dataclass(slots=True)
class Chain:
    company: str
    aspect_id: str
    canonical: str
    years: list[int]
    statements: list[str]


class DuckDBGraphStore:
    """Thin, explicit SQL. No ORM, so the queries in the paper are the queries in the code."""

    def __init__(
        self, db_path: str | Path, read_only: bool = False, memory_limit: str = "1GB", threads: int = 2
    ) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.path), read_only=read_only)
        # The build runs next to a PDF parser on a laptop; keep DuckDB from taking the machine down.
        self.con.execute(f"SET memory_limit='{memory_limit}'")
        self.con.execute(f"SET threads={threads}")
        if not read_only:
            self.con.execute(SCHEMA)

    # ------------------------------------------------------------------ writes
    def insert_many(self, table: str, rows: list[tuple], columns: int) -> None:
        if not rows:
            return
        placeholders = ", ".join(["?"] * columns)
        self.con.executemany(f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})", rows)

    def checkpoint(self) -> None:
        """Flush the WAL so a long build does not accumulate one giant write-ahead log."""
        self.con.execute("CHECKPOINT")

    def clear(self, *tables: str) -> None:
        for t in tables:
            self.con.execute(f"DELETE FROM {t}")

    # ------------------------------------------------------------------ reads
    def counts(self) -> dict[str, int]:
        out = {}
        for t in ("companies", "reports", "statements", "aspects", "aspect_aliases", "mentions",
                  "follows_up"):
            out[t] = self.con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        return out

    def chains(self, min_years: int = 2) -> list[Chain]:
        """(company, aspect) groups whose statements span at least `min_years` distinct years."""
        rows = self.con.execute(
            """
            SELECT s.company, m.aspect_id, any_value(a.canonical),
                   list(DISTINCT s.year ORDER BY s.year), list(s.stmt_id)
            FROM mentions m
            JOIN statements s USING (stmt_id)
            JOIN aspects a ON a.aspect_id = m.aspect_id
            GROUP BY s.company, m.aspect_id
            HAVING count(DISTINCT s.year) >= ?
            ORDER BY count(DISTINCT s.year) DESC, s.company
            """,
            [min_years],
        ).fetchall()
        return [Chain(c, aid, canon, list(years), list(stmts)) for c, aid, canon, years, stmts in rows]

    def statements_for(
        self, company: str, aspect_id: str, year_from: int | None = None, year_to: int | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT s.stmt_id, s.text, s.company, s.year, s.page, s.sha256, m.action, m.method
            FROM mentions m JOIN statements s USING (stmt_id)
            WHERE s.company = ? AND m.aspect_id = ?
        """
        params: list[Any] = [company, aspect_id]
        if year_from is not None:
            sql += " AND s.year >= ?"
            params.append(year_from)
        if year_to is not None:
            sql += " AND s.year <= ?"
            params.append(year_to)
        sql += " ORDER BY s.year, s.page"
        cols = ["stmt_id", "text", "company", "year", "page", "sha256", "action", "method"]
        return [dict(zip(cols, r, strict=True)) for r in self.con.execute(sql, params).fetchall()]

    def find_aspect(self, key: str) -> str | None:
        row = self.con.execute("SELECT aspect_id FROM aspect_aliases WHERE surface = ?", [key]).fetchone()
        return row[0] if row else None

    def subgraph(self, company: str, aspect_id: str | None = None) -> nx.MultiDiGraph:
        """Company-scoped subgraph for traversal. Small by construction: hundreds of nodes."""
        g = nx.MultiDiGraph()
        sql = """
            SELECT s.stmt_id, s.text, s.year, s.page, m.aspect_id, a.canonical, a.category, m.action
            FROM mentions m
            JOIN statements s USING (stmt_id)
            JOIN aspects a ON a.aspect_id = m.aspect_id
            WHERE s.company = ?
        """
        params: list[Any] = [company]
        if aspect_id:
            sql += " AND m.aspect_id = ?"
            params.append(aspect_id)
        for stmt_id, text, year, page, aid, canonical, category, action in self.con.execute(
            sql, params
        ).fetchall():
            g.add_node(stmt_id, kind="statement", text=text, year=year, page=page, company=company)
            g.add_node(aid, kind="aspect", canonical=canonical, category=category)
            g.add_edge(stmt_id, aid, key="mentions", action=action)
        for a, b, aid, years, same in self.con.execute(
            "SELECT from_stmt, to_stmt, aspect_id, years_apart, same_text FROM follows_up "
            "WHERE company = ?",
            [company],
        ).fetchall():
            if g.has_node(a) and g.has_node(b):
                g.add_edge(a, b, key="follows_up", aspect_id=aid, years_apart=years, same_text=same)
        return g

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> DuckDBGraphStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
