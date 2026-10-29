"""Template for your own system. Copy `src/example-rag` to `src/<your-name>-rag`, rename the package,
the entry point and `name`, add the folder to `[tool.uv.workspace].members` in the root pyproject,
run `uv sync`, and `uv run gw-eval --list` shows it.

What is here is the smallest honest system: BM25 over the shared chunk store with the company and
year filters every condition requires, and the shared classifier. Replace `retrieve` (and, only if the
classifier *is* your contribution, `classifier`) and keep the rest.

Rules the harness relies on (README §6):
- honour `query.company`, `query.year_from` / `year_to`, and skip `query.anchor_year` when the
  condition starts with `cross_year`;
- never return the target sentence (the harness drops it and counts it anyway);
- each `EvidenceSpan` carries `company`, `year`, `page`, `file` and a `why` tag, so citations resolve;
- a classifier returns `rationale` and `citations`, not just a label.
"""

from __future__ import annotations

from collections import defaultdict

from baseline_rag import chunks as chunk_store
from baseline_rag.index import BM25
from gw_common.classifiers.llm_action import LLMActionClassifier
from gw_common.evidence import is_target_span
from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvidenceCondition, EvidenceSpan, Query


class Bm25SameCompanyRetriever:
    def __init__(self, build_id: str = chunk_store.DEFAULT_BUILD) -> None:
        self.chunks, _vectors, self.manifest = chunk_store.load(build_id)   # the shared KB, as-is
        self.index = BM25([c.indexed_text() for c in self.chunks])
        self.by_company: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(self.chunks):
            self.by_company[c.company].append(i)

    def retrieve(self, query: Query, *, k: int = 10) -> list[EvidenceSpan]:
        cross_year = query.condition.value.startswith("cross_year")
        allowed = {
            i for i in self.by_company.get(query.company or "", [])
            if not (cross_year and self.chunks[i].year == query.anchor_year)
            and (query.year_from is None or self.chunks[i].year >= query.year_from)
            and (query.year_to is None or self.chunks[i].year <= query.year_to)
        }
        if not allowed:
            return []
        text = f"{query.aspect}. {query.text}" if query.aspect else query.text
        out = []
        for i, score in self.index.search(text, allowed, k=k + 3):
            c = self.chunks[i]
            span = EvidenceSpan(statement_id=c.chunk_id, text=c.text, company=c.company, year=c.year,
                                page=c.page, file=c.file, score=round(float(score), 3), why="example:bm25")
            if is_target_span(span, query):
                continue
            out.append(span)
            if len(out) >= k:
                break
        return out


class ExampleRagSystem(BaseSystem):
    name = "example-rag"

    def __init__(self) -> None:
        self._retriever: Bm25SameCompanyRetriever | None = None
        self._classifier: LLMActionClassifier | None = None

    def supported_conditions(self) -> list[EvidenceCondition]:
        return [EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.LOCAL,
                EvidenceCondition.SAME_REPORT_RRF, EvidenceCondition.CROSS_YEAR_RRF]

    def retriever(self):
        if self._retriever is None:
            self._retriever = Bm25SameCompanyRetriever()
        return self._retriever

    def classifier(self):
        if self._classifier is None:
            self._classifier = LLMActionClassifier()      # shared: the comparison stays about retrieval
        return self._classifier


def build_system() -> ExampleRagSystem:
    return ExampleRagSystem()
