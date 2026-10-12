"""Agentic RAG: a bounded plan-retrieve-stop loop over the shared passage store (`cross_year_agentic`).

The comparison it exists for is budget against performance: does letting an LLM plan and rewrite the
search buy enough macro-F1 to pay for its extra calls? So the system keeps everything else fixed:

- the shared classifier, prompt and evidence budget (k = 3, 800 characters), like every other arm;
- the same base search for its own `same_report_rrf` / `cross_year_rrf` arms, so `cross_year_rrf`
  against `cross_year_agentic` in one run is a paired comparison that differs only in the agent;
- the agent's chat tokens are added to each `cross_year_agentic` prediction (`input_tokens`,
  `output_tokens`), and its planner calls are reported as `graph_hops`, so the harness's cost and
  hop figures are end to end. `llm_calls` is left as the classifier's, because the harness derives
  `cached_calls` from it. Retrieval runs once per condition while the classifier runs once per
  repeat, so per-item cost is right and the run total counts the agent `repeats` times.

Per-item traces (planner decisions, queries, stop reason) are appended to
`artifacts/agentic/traces.jsonl`. Budget knobs are documented in `agentic_rag.agent`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from gw_common.classifiers.llm_action import LLMActionClassifier
from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvalItem, EvidenceCondition, EvidenceSpan, Prediction

from agentic_rag.agent import AgenticRetriever, trace_key


class AgentCostClassifier:
    """The shared classifier, unchanged, plus the agent's retrieval-time cost on each prediction."""

    def __init__(self, inner: LLMActionClassifier, retriever: AgenticRetriever) -> None:
        self.inner, self.retriever = inner, retriever

    def describe(self) -> dict[str, object]:
        return {**self.inner.describe(), "agent": self.retriever.describe()}

    def classify(
        self,
        items: Sequence[EvalItem],
        *,
        condition: EvidenceCondition,
        evidence: Mapping[str, list[EvidenceSpan]] | None = None,
    ) -> list[Prediction]:
        preds = self.inner.classify(items, condition=condition, evidence=evidence)
        if condition is not EvidenceCondition.CROSS_YEAR_AGENTIC:
            return preds
        out = []
        for item, p in zip(items, preds, strict=True):
            t = self.retriever.traces.get(trace_key(item.company, item.year, item.text))
            if t is not None:
                p = p.model_copy(update={"input_tokens": p.input_tokens + t.input_tokens,
                                         "output_tokens": p.output_tokens + t.output_tokens,
                                         "graph_hops": t.hops})
            out.append(p)
        return out


class AgenticRagSystem(BaseSystem):
    name = "agentic-rag"

    def __init__(self, build_id: str = "dev") -> None:
        self.build_id = os.getenv("GW_BASELINE_BUILD", build_id)
        self._retriever: AgenticRetriever | None = None
        self._classifier: AgentCostClassifier | None = None

    def supported_conditions(self) -> list[EvidenceCondition]:
        return [EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.LOCAL,
                EvidenceCondition.SAME_REPORT_RRF, EvidenceCondition.CROSS_YEAR_RRF,
                EvidenceCondition.CROSS_YEAR_AGENTIC]

    def retriever(self) -> AgenticRetriever:
        if self._retriever is None:
            self._retriever = AgenticRetriever(self.build_id)
        return self._retriever

    def classifier(self) -> AgentCostClassifier:
        if self._classifier is None:
            self._classifier = AgentCostClassifier(LLMActionClassifier(), self.retriever())
        return self._classifier


def build_system() -> AgenticRagSystem:
    return AgenticRagSystem()
