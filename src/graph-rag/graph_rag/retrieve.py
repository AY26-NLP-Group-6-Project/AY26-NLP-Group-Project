"""Cross-year evidence retrieval for the PoC.

`cross_year_graph`: follow the graph from the item's aspect to statements of the **same company in
other years** that mention the same (canonical) aspect.

`cross_year_fused`: the same, and when the graph yields fewer than k statements, fill the rest with
BM25 over the company's other-year statements. This is the "textual recovery" pattern: robust GraphRAG
work on imperfect LLM-built graphs (arXiv 2603.14828) falls back to text instead of forcing uncertain
graph bindings, and systematic RAG vs GraphRAG comparisons find integration beats either alone
(arXiv 2502.11371).

Ranking inside each source is deliberately simple for a PoC: nearest years first, then word overlap
with the target sentence; BM25 scores rank the fallback.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache

from gw_common.evidence import is_target_span
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query
from gw_common.text import is_statement

from graph_rag.build.text import aspect_key
from graph_rag.config import GraphConfig
from graph_rag.store.duckdb_store import GROUP_ID, DuckDBGraphStore

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set(
    "the a an and or of to in for on with by at from as is are was were be been our we its their this "
    "that these those it has have had will shall can may also which who all any".split()
)


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 2]


class GraphRetriever:
    def __init__(self, cfg: GraphConfig | None = None) -> None:
        self.cfg = cfg or GraphConfig.load("configs/graph.dev.yaml")
        if not self.cfg.db_path.exists():
            raise FileNotFoundError(
                f"graph store not found at {self.cfg.db_path}. graph-rag needs the parsed corpus and claim "
                "graph: build it with `gw-graph build` (requires the reports under kb/raw/) or copy "
                "artifacts/graph/<build>/graph.duckdb from a teammate. baseline-rag and example-rag "
                "need only the chunk store."
            )
        self.store = DuckDBGraphStore(self.cfg.db_path, read_only=True)

    def describe(self) -> dict:
        """What the run retrieved over; the runner writes it into the manifest."""
        statements = self.store.con.execute("SELECT count(*) FROM statements").fetchone()[0]
        return {"store": "graph", "graph_build_id": self.cfg.build_id, "statements": statements,
                "unit": "statement"}

    # --------------------------------------------------------------- graph
    def _group_for(self, aspect: str | None) -> str | None:
        if not aspect:
            return None
        row = self.store.con.execute(
            f"""
            SELECT {GROUP_ID}
            FROM aspect_aliases al
            JOIN mentions m ON m.aspect_id = al.aspect_id
            LEFT JOIN aspect_canon c ON c.aspect_id = m.aspect_id
            WHERE al.surface = ? LIMIT 1
            """,
            [aspect_key(aspect)],
        ).fetchone()
        return row[0] if row else None

    def _graph_hits(self, query: Query, anchor_year: int | None, k: int) -> list[EvidenceSpan]:
        gid = self._group_for(query.aspect)
        if gid is None or not query.company:
            return []
        rows = self.store.statements_for(query.company, gid)
        q = set(_tokens(query.text))
        seen, out = set(), []
        rows = [r for r in rows if r["year"] != anchor_year]
        rows.sort(key=lambda r: (abs((anchor_year or r["year"]) - r["year"]),
                                 -len(q & set(_tokens(r["text"])))))
        for r in rows:
            norm = " ".join(_tokens(r["text"]))
            if norm in seen:                      # templated reports repeat sentences verbatim
                continue
            seen.add(norm)
            span = EvidenceSpan(statement_id=r["stmt_id"], text=r["text"], company=r["company"],
                                year=r["year"], page=r["page"], file=r["sha256"], score=1.0,
                                why=f"graph:{r['method']}")
            if is_target_span(span, query):
                continue
            out.append(span)
            if len(out) >= k:
                break
        return out

    # --------------------------------------------------------------- bm25 fallback
    @lru_cache(maxsize=64)  # noqa: B019 - one retriever per run, bounded cache
    def _company_index(self, company: str):
        rows = self.store.con.execute(
            "SELECT stmt_id, text, year, page, sha256 FROM statements WHERE company = ?", [company]
        ).fetchall()
        docs = [(sid, text, year, page, sha)
                for sid, text, year, page, sha in rows if is_statement(text)]
        toks = [_tokens(d[1]) for d in docs]
        df = Counter(t for ts in toks for t in set(ts))
        avgdl = sum(len(t) for t in toks) / max(1, len(toks))
        return docs, toks, df, avgdl

    def _bm25_hits(self, query: Query, anchor_year: int | None, k: int, exclude: set[str],
                   k1: float = 1.5, b: float = 0.75) -> list[EvidenceSpan]:
        if not query.company:
            return []
        docs, toks, df, avgdl = self._company_index(query.company)
        n = len(docs)
        q = _tokens(f"{query.aspect or ''} {query.text}")
        scored = []
        for (sid, text, year, page, sha), ts in zip(docs, toks, strict=True):
            if year == anchor_year or sid in exclude:
                continue
            tf = Counter(ts)
            s = 0.0
            for t in q:
                if t in tf:
                    idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                    s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(ts) / avgdl))
            if s > 0:
                scored.append((s, sid, text, year, page, sha))
        scored.sort(reverse=True)
        out = []
        for s, sid, text, year, page, sha in scored:
            span = EvidenceSpan(statement_id=sid, text=text, company=query.company, year=year, page=page,
                                file=sha, score=round(s, 3), why="bm25")
            if not is_target_span(span, query):
                out.append(span)
            if len(out) >= k:
                break
        return out

    # --------------------------------------------------------------- promise window (RQ2)
    def _promise_finder(self):
        """The trajectory finder, built on first use: it needs the promise table (for linked targets) and
        an embedding client."""
        if getattr(self, "_finder", None) is None:
            from gw_common.llm import LLMClient

            from graph_rag.promises.evidence import TrajectoryFinder
            from graph_rag.promises.extract import out_dir

            path = out_dir(self.cfg) / "promises.jsonl"
            promises = {}
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line:
                        p = json.loads(line)
                        promises[p["promise_id"]] = p
            self._finder = TrajectoryFinder(self.cfg, LLMClient(), promises)
        return self._finder

    def _promise_window(self, query: Query, k: int) -> list[EvidenceSpan]:
        from graph_rag.promises.evidence import promise_of, spans_of

        promise = promise_of(query)
        return spans_of(self._promise_finder().find(promise), promise["company"])[:k]

    # --------------------------------------------------------------- protocol
    def retrieve(self, query: Query, *, k: int = 3) -> list[EvidenceSpan]:
        if query.condition is EvidenceCondition.PROMISE_WINDOW:
            return self._promise_window(query, k)
        anchor = query.anchor_year
        hits = self._graph_hits(query, anchor, k)
        if query.condition is EvidenceCondition.CROSS_YEAR_FUSED and len(hits) < k:
            hits += self._bm25_hits(query, anchor, k - len(hits), {h.statement_id for h in hits})
        return hits
