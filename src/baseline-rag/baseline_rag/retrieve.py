"""Hybrid retriever: BM25 + dense, fused with RRF, reranked by a cross-encoder.

This is the "ordinary RAG" arm every other arm is measured against. It honours the condition's
company and year filters (`same_report` stays inside the item's own report, `cross_year` looks at the
same company's other years), which is also what RQ3 asks about: does metadata filtering reduce
wrong-company retrieval.

The stage list is configurable so the retrieval ablation can run `bm25` / `dense` / `rrf` /
`rrf+rerank` through the same code path.
"""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from gw_common.llm import LLMClient
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query

from baseline_rag import chunks as chunk_store
from baseline_rag.index import BM25, CANDIDATES, RERANK_DEPTH, CrossEncoderReranker, Dense, rrf

MODES = ("bm25", "dense", "rrf", "rrf+rerank")


class HybridRetriever:
    def __init__(self, build_id: str = "dev", mode: str = "rrf+rerank",
                 client: LLMClient | None = None) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.mode = mode
        self.chunks, vectors, self.manifest = chunk_store.load(build_id)
        self.bm25 = BM25([c.indexed_text() for c in self.chunks])
        self.dense = Dense(vectors)
        self.reranker = CrossEncoderReranker() if mode.endswith("rerank") else None
        self.client = client or LLMClient()
        self._by_company: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(self.chunks):
            self._by_company[c.company].append(i)

    # ------------------------------------------------------------------ filters
    def _allowed(self, query: Query) -> set[int] | None:
        if not query.company:
            return None
        idx = self._by_company.get(query.company, [])
        anchor = query.anchor_year
        cross_year = query.condition.value.startswith("cross_year")
        keep = set()
        for i in idx:
            year = self.chunks[i].year
            if cross_year and anchor is not None and year == anchor:
                continue            # cross-year evidence must come from another report
            if query.year_from is not None and year < query.year_from:
                continue
            if query.year_to is not None and year > query.year_to:
                continue
            keep.add(i)
        return keep

    @lru_cache(maxsize=4096)  # noqa: B019 - one retriever per run; the query text repeats across arms
    def _query_vector(self, text: str) -> tuple[float, ...]:
        return tuple(self.client.embed([text])[0])

    # ------------------------------------------------------------------ protocol
    def retrieve(self, query: Query, *, k: int = 3) -> list[EvidenceSpan]:
        allowed = self._allowed(query)
        if allowed is not None and not allowed:
            return []
        text = f"{query.aspect}. {query.text}" if query.aspect else query.text

        if self.mode == "bm25":
            ranked = self.bm25.search(text, allowed, CANDIDATES)
        elif self.mode == "dense":
            ranked = self.dense.search(self._query_vector(text), allowed, CANDIDATES)
        else:
            ranked = rrf(self.bm25.search(text, allowed, CANDIDATES),
                         self.dense.search(self._query_vector(text), allowed, CANDIDATES))

        if self.reranker is not None and ranked:
            head = ranked[:RERANK_DEPTH]
            scores = self.reranker.rerank(text, [self.chunks[i].text for i, _ in head])
            ranked = sorted(zip([i for i, _ in head], scores, strict=True),
                            key=lambda kv: -kv[1]) + ranked[RERANK_DEPTH:]

        why = {"bm25": "bm25", "dense": "dense", "rrf": "rrf", "rrf+rerank": "rrf+rerank"}[self.mode]
        out = []
        for i, score in ranked[:k]:
            c = self.chunks[i]
            out.append(EvidenceSpan(statement_id=c.chunk_id, text=c.text, company=c.company,
                                    year=c.year, page=c.page, file=c.file, score=round(float(score), 4),
                                    why=why))
        return out


def supported_conditions() -> list[EvidenceCondition]:
    return [
        EvidenceCondition.SENTENCE_ONLY,
        EvidenceCondition.LOCAL,
        EvidenceCondition.SAME_REPORT_RRF,
        EvidenceCondition.CROSS_YEAR_RRF,
    ]
