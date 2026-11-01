"""The corpus as a set of tools: what any retriever, fixed or agentic, may call.

A fixed retriever is one plan over these calls (the hybrid baseline: one `search`, hybrid mode, k spans).
An agentic retriever is a planner over the same calls: search, read the hits' neighbours, open a page,
look at which reports a company has, search again, stop. Both end in `Retriever.retrieve`, so the
evaluation does not care which; what it measures is the same.

Nothing here reads a store. Implementations register under the entry-point group `gw.corpora`
(`statements`: the chunk store of every statement, in `baseline_rag.corpus`; `graph`: the same plus the
claim graph's joins, in `graph_rag.corpus`) and are loaded by name with `load()`, so a system package
needs no import of another system package.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from gw_common.schemas import EvidenceSpan

GROUP = "gw.corpora"
SEARCH_MODES = ("bm25", "dense", "hybrid", "hybrid+rerank")


class Report(BaseModel):
    """One sustainability report as the corpus holds it."""

    company: str
    year: int
    file: str          # sha256 of the PDF, the `file` of every span from it
    pages: int
    statements: int


@runtime_checkable
class Corpus(Protocol):
    """Read access to the statements of every report; every result is an `EvidenceSpan`."""

    def search(self, text: str, *, company: str | None = None, year_from: int | None = None,
               year_to: int | None = None, exclude_year: int | None = None, k: int = 10,
               mode: str = "hybrid") -> list[EvidenceSpan]:
        """Statements ranked against `text` inside the filters; `mode` is one of SEARCH_MODES."""

    def get(self, statement_id: str) -> EvidenceSpan | None:
        """One statement by id, or None."""

    def neighbours(self, statement_id: str, *, before: int = 1, after: int = 1) -> list[EvidenceSpan]:
        """The statements around one, on the same page of the same report, in report order (the
        statement itself included)."""

    def page(self, company: str, year: int, page: int) -> list[EvidenceSpan]:
        """Every statement of one page, in report order."""

    def reports(self, company: str) -> list[Report]:
        """The company's reports, oldest first."""

    def companies(self) -> list[str]:
        """Every company in the corpus."""


def available() -> dict[str, str]:
    """name -> entry point target."""
    return {ep.name: ep.value for ep in entry_points(group=GROUP)}


def load(name: str = "statements", **kwargs) -> Corpus:
    """Instantiate a registered corpus; keyword arguments go to its constructor (e.g. `build_id`)."""
    for ep in entry_points(group=GROUP):
        if ep.name == name:
            corpus = ep.load()(**kwargs)
            if not isinstance(corpus, Corpus):
                raise TypeError(f"{ep.value} does not satisfy the Corpus protocol")
            return corpus
    known = ", ".join(sorted(available())) or "(none installed)"
    raise KeyError(f"unknown corpus {name!r}. Registered corpora: {known}")
