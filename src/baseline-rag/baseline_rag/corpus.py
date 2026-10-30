"""The statement store as a corpus: the tools of `gw_common.corpus.Corpus` over the chunk store.

Built for the `statements` store, where one chunk is one statement and the chunks sit in report order
(report, page, index), so neighbours and pages are list positions. Search is the hybrid baseline's own
ranking (`HybridRetriever.rank`) with the mode chosen per call, so an agent that calls `search` gets
exactly what the fixed baseline gets, and may then read around the hits.
"""

from __future__ import annotations

from collections import defaultdict

from gw_common.corpus import SEARCH_MODES, Report
from gw_common.llm import LLMClient
from gw_common.schemas import EvidenceSpan

from baseline_rag.chunks import DEFAULT_BUILD
from baseline_rag.retrieve import HybridRetriever

_MODE = {"bm25": "bm25", "dense": "dense", "hybrid": "rrf", "hybrid+rerank": "rrf+rerank"}


class ChunkCorpus:
    name = "statements"

    def __init__(self, build_id: str = DEFAULT_BUILD, client: LLMClient | None = None,
                 backend: str = "files") -> None:
        self.retriever = HybridRetriever(build_id, mode="rrf", client=client, backend=backend)
        self.chunks = self.retriever.chunks
        self._at = {c.chunk_id: i for i, c in enumerate(self.chunks)}
        self._pages: dict[tuple[str, int, int | None], list[int]] = defaultdict(list)
        self._reports: dict[str, dict[tuple[int, str], list[int]]] = defaultdict(lambda: defaultdict(list))
        for i, c in enumerate(self.chunks):
            self._pages[(c.company, c.year, c.page)].append(i)
            self._reports[c.company][(c.year, c.file)].append(i)

    def describe(self) -> dict:
        return {**self.retriever.describe(), "corpus": self.name}

    def _span(self, i: int, why: str, score: float = 0.0) -> EvidenceSpan:
        c = self.chunks[i]
        return EvidenceSpan(statement_id=c.chunk_id, text=c.text, company=c.company, year=c.year,
                            page=c.page, file=c.file, score=score, why=why)

    # ----------------------------------------------------------------- Corpus
    def search(self, text: str, *, company: str | None = None, year_from: int | None = None,
               year_to: int | None = None, exclude_year: int | None = None, k: int = 10,
               mode: str = "hybrid") -> list[EvidenceSpan]:
        if mode not in SEARCH_MODES:
            raise ValueError(f"mode must be one of {SEARCH_MODES}")
        allowed = self.retriever.allowed_ids(company, year_from, year_to, exclude_year)
        if allowed is not None and not allowed:
            return []
        return self.retriever.spans(self.retriever.rank(text, allowed, _MODE[mode]), k, why=mode)

    def get(self, statement_id: str) -> EvidenceSpan | None:
        i = self._at.get(statement_id)
        return None if i is None else self._span(i, "lookup")

    def neighbours(self, statement_id: str, *, before: int = 1, after: int = 1) -> list[EvidenceSpan]:
        i = self._at.get(statement_id)
        if i is None:
            return []
        c = self.chunks[i]
        page = self._pages[(c.company, c.year, c.page)]
        at = page.index(i)
        return [self._span(j, "neighbour") for j in page[max(0, at - before):at + after + 1]]

    def page(self, company: str, year: int, page: int) -> list[EvidenceSpan]:
        return [self._span(j, "page") for j in self._pages.get((company, year, page), [])]

    def reports(self, company: str) -> list[Report]:
        out = []
        for (year, file), positions in sorted(self._reports.get(company, {}).items()):
            pages = max((self.chunks[j].page or 0) for j in positions)
            out.append(Report(company=company, year=year, file=file, pages=pages, statements=len(positions)))
        return out

    def companies(self) -> list[str]:
        return sorted(self._reports)
