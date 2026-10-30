"""Temporal claim graph system.

PoC arms (2026-09-13): sentence_only and local run the shared LLM classifier without retrieval;
cross_year_graph adds same-company other-year statements reached through the aspect graph;
cross_year_fused fills missing graph evidence with BM25 over the company's other-year text.
"""

from __future__ import annotations

from gw_common.interfaces import ActionClassifier, BaseSystem, Retriever
from gw_common.schemas import EvidenceCondition


class GraphRagSystem(BaseSystem):
    name = "graph-rag"

    def __init__(self) -> None:
        self._retriever = None
        self._classifier = None

    def supported_conditions(self) -> list[EvidenceCondition]:
        return [EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.LOCAL,
                EvidenceCondition.CROSS_YEAR_GRAPH, EvidenceCondition.CROSS_YEAR_FUSED,
                EvidenceCondition.PROMISE_WINDOW]

    def retriever(self) -> Retriever | None:
        if self._retriever is None:
            from graph_rag.retrieve import GraphRetriever

            self._retriever = GraphRetriever()
        return self._retriever

    def classifier(self) -> ActionClassifier | None:
        if self._classifier is None:
            from gw_common.classifiers.llm_action import LLMActionClassifier

            self._classifier = LLMActionClassifier()
        return self._classifier


def build_system() -> GraphRagSystem:
    return GraphRagSystem()
