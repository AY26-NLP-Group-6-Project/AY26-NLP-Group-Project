"""The statement corpus plus the claim graph's joins, as tools an agent may call.

Everything `ChunkCorpus` offers (search, get, neighbours, page, reports), and three lookups the graph
holds: which aspects a statement mentions, which later statements of the same company follow it up on
an aspect, and which other dated targets the company set on a metric (the promise table's join).
"""

from __future__ import annotations

import json
from functools import cached_property

from baseline_rag.chunks import DEFAULT_BUILD
from baseline_rag.corpus import ChunkCorpus
from gw_common.llm import LLMClient
from gw_common.schemas import EvidenceSpan

from graph_rag.build.text import aspect_key
from graph_rag.config import GraphConfig
from graph_rag.promises.extract import out_dir
from graph_rag.store.duckdb_store import DuckDBGraphStore


class GraphCorpus(ChunkCorpus):
    name = "graph"

    def __init__(self, build_id: str = DEFAULT_BUILD, cfg: GraphConfig | None = None,
                 client: LLMClient | None = None) -> None:
        super().__init__(build_id, client)
        self.cfg = cfg or GraphConfig.load("configs/graph.dev.yaml")
        self.store = DuckDBGraphStore(self.cfg.db_path, read_only=True)

    def describe(self) -> dict:
        return {**super().describe(), "corpus": self.name, "graph_build_id": self.cfg.build_id}

    @cached_property
    def promises(self) -> list[dict]:
        path = out_dir(self.cfg) / "promises.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def _statement(self, stmt_id: str, why: str) -> EvidenceSpan | None:
        span = self.get(stmt_id)
        if span is not None:
            return span.model_copy(update={"why": why})
        row = self.store.con.execute(
            "SELECT text, company, year, page, sha256 FROM statements WHERE stmt_id = ?", [stmt_id]
        ).fetchone()
        if row is None:
            return None
        return EvidenceSpan(statement_id=stmt_id, text=row[0], company=row[1], year=row[2], page=row[3],
                            file=row[4], why=why)

    # ----------------------------------------------------------------- graph joins
    def aspects(self, statement_id: str) -> list[dict]:
        """The aspects a statement mentions, with the action label where one exists."""
        rows = self.store.con.execute(
            """
            SELECT a.canonical, a.category, m.action, m.method
            FROM mentions m JOIN aspects a ON a.aspect_id = m.aspect_id
            WHERE m.stmt_id = ? ORDER BY a.canonical
            """,
            [statement_id],
        ).fetchall()
        return [{"aspect": r[0], "category": r[1], "action": r[2], "method": r[3]} for r in rows]

    def follow_ups(self, statement_id: str) -> list[EvidenceSpan]:
        """Later statements of the same company on the same aspect, nearest year first; `why` says how
        many years later and whether the text is a verbatim repeat."""
        rows = self.store.con.execute(
            "SELECT to_stmt, years_apart, same_text FROM follows_up WHERE from_stmt = ? "
            "ORDER BY years_apart, to_stmt", [statement_id]
        ).fetchall()
        out = []
        for to_stmt, years, same in rows:
            span = self._statement(to_stmt, f"graph:follows_up:+{years}y{':repeat' if same else ''}")
            if span is not None:
                out.append(span)
        return out

    def related_targets(self, company: str, metric: str) -> list[dict]:
        """The company's dated targets on this metric (normalised match or a `related` link), oldest first."""
        key = aspect_key(metric)
        direct = [p for p in self.promises if p["company"] == company and aspect_key(p["metric"]) == key]
        linked_ids = {r["promise_id"] for p in direct for r in p.get("related", [])}
        linked = [p for p in self.promises if p["promise_id"] in linked_ids and p not in direct]
        return sorted(direct + linked, key=lambda p: (p["origin"]["year"], p["target_year"]))
