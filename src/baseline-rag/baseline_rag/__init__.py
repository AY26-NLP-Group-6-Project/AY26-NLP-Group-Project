"""Hybrid BM25 + dense + RRF + cross-encoder baseline: the "ordinary RAG" arm.

Same classifier and same evidence budget as every other system, so a comparison against the graph
arms measures retrieval, not prompting.
"""

from __future__ import annotations

import os

from gw_common.classifiers.llm_action import LLMActionClassifier
from gw_common.interfaces import ActionClassifier, BaseSystem, Retriever
from gw_common.schemas import EvidenceCondition

from baseline_rag.chunks import DEFAULT_BUILD
from baseline_rag.retrieve import HybridRetriever, supported_conditions


class BaselineRagSystem(BaseSystem):
    name = "baseline-rag"

    def __init__(self, build_id: str = DEFAULT_BUILD, mode: str | None = None) -> None:
        self.build_id = os.getenv("GW_BASELINE_BUILD", build_id)
        self.mode = mode or os.getenv("GW_BASELINE_MODE", "rrf+rerank")
        self.backend = os.getenv("GW_BASELINE_BACKEND", "files")
        self._retriever: HybridRetriever | None = None
        self._classifier: LLMActionClassifier | None = None

    def supported_conditions(self) -> list[EvidenceCondition]:
        return supported_conditions()

    def retriever(self) -> Retriever | None:
        if self._retriever is None:
            self._retriever = HybridRetriever(self.build_id, self.mode, backend=self.backend)
        return self._retriever

    def classifier(self) -> ActionClassifier | None:
        if self._classifier is None:
            self._classifier = LLMActionClassifier()
        return self._classifier


def build_system() -> BaselineRagSystem:
    return BaselineRagSystem()
