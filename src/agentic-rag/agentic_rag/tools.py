"""The corpus as the agent may call it: every call fenced to the query's company and years.

The planner names queries and statements; this layer decides what comes back. A planner that asks for a
year outside the window, or a statement of another company, gets nothing, so no prompt can widen what an
arm is allowed to read, and the sentence being classified never comes back.
"""

from __future__ import annotations

from gw_common.corpus import Corpus
from gw_common.evidence import is_target_span
from gw_common.schemas import EvidenceSpan, Query


class Fence:
    def __init__(self, corpus: Corpus, query: Query) -> None:
        self.corpus, self.query = corpus, query
        self.company = query.company
        self.year_from, self.year_to = query.year_from, query.year_to
        cross_year = query.condition.value.startswith("cross_year")
        self.exclude_year = query.anchor_year if cross_year else None

    def allows(self, span: EvidenceSpan) -> bool:
        if span.company != self.company or span.year == self.exclude_year:
            return False
        if (self.year_from is not None and span.year < self.year_from) or (
            self.year_to is not None and span.year > self.year_to
        ):
            return False
        return not is_target_span(span, self.query)

    def years(self) -> list[int]:
        """The company's report years this arm may read, oldest first."""
        years = sorted({r.year for r in self.corpus.reports(self.company)})
        return [y for y in years if (self.year_from is None or y >= self.year_from)
                and (self.year_to is None or y <= self.year_to) and y != self.exclude_year]

    def search(self, text: str, *, year: int | None = None, k: int = 5,
               mode: str = "hybrid") -> list[EvidenceSpan]:
        if year is not None and year not in self.years():
            return []
        spans = self.corpus.search(text, company=self.company,
                                   year_from=year if year is not None else self.year_from,
                                   year_to=year if year is not None else self.year_to,
                                   exclude_year=self.exclude_year, k=k + 1, mode=mode)
        return [s for s in spans if self.allows(s)][:k]

    def around(self, statement_id: str, *, before: int = 1, after: int = 1) -> list[EvidenceSpan]:
        """The statements around one in report order, the statement itself left out."""
        spans = self.corpus.neighbours(statement_id, before=before, after=after)
        return [s for s in spans if s.statement_id != statement_id and self.allows(s)]

    def page(self, year: int, page: int) -> list[EvidenceSpan]:
        return [s for s in self.corpus.page(self.company, year, page) if self.allows(s)]

    def around_target(self, *, before: int = 2, after: int = 2) -> list[EvidenceSpan]:
        """The statements next to the sentence being classified, when the arm may read its report."""
        page = self.query.meta.get("page")
        year = self.query.anchor_year
        if page is None or year is None or year == self.exclude_year:
            return []
        on_page = self.corpus.page(self.company, year, page)
        at = next((i for i, s in enumerate(on_page) if is_target_span(s, self.query)), None)
        if at is None:
            return []
        return [s for s in on_page[max(0, at - before):at + after + 1] if self.allows(s)]
