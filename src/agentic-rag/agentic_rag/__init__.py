"""Agentic RAG: a bounded planner over the shared corpus tools, for both research questions.

The comparison it exists for is budget against performance: does letting an LLM decide what to look for buy
enough to pay for its extra calls? So everything else is kept fixed: the shared classifier and judge, their
prompts and evidence budgets; the knowledge base (`gw_common.corpus.load("statements")`); and the arm's own
fixed searches (`same_report_rrf`, `cross_year_rrf`), the hybrid baseline's ranking, so one run compares the
fixed and the agentic arm on the same items.

| condition | policy |
|---|---|
| `cross_year_agentic` | `rq1.py`, other years only: like for like with `cross_year_rrf` |
| `company_agentic` | `rq1.py`, every report of the company, starting next to the sentence |
| `promise_window` | `rq2.py`, the window of a dated commitment |

Cost is charged end to end. On RQ1 the planner's tokens are added to each prediction and its calls reported
as `graph_hops`, and `llm_calls` is left as the classifier's because the harness derives `cached_calls` from
it. Retrieval runs once per condition while the classifier runs once per repeat, so per-item cost is right
and a run's total counts the planner `repeats` times. On RQ2 the run reports the planner next to the judge.
Per-item traces go to `artifacts/agentic/traces-*.jsonl`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from baseline_rag.chunks import DEFAULT_BUILD
from gw_common.classifiers.llm_action import LLMActionClassifier
from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvalItem, EvidenceCondition, EvidenceSpan, Prediction

from agentic_rag.agent import AgenticRetriever, trace_key

CHARGED = (EvidenceCondition.CROSS_YEAR_AGENTIC, EvidenceCondition.COMPANY_AGENTIC)


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
        if condition not in CHARGED:
            return preds
        out = []
        for item, p in zip(items, preds, strict=True):
            t = self.retriever.traces.get(trace_key(condition.value, item.company, item.year, item.text))
            if t is not None:
                p = p.model_copy(update={"input_tokens": p.input_tokens + t.input_tokens,
                                         "output_tokens": p.output_tokens + t.output_tokens,
                                         "graph_hops": t.hops})
            out.append(p)
        return out


class AgenticRagSystem(BaseSystem):
    name = "agentic-rag"

    def __init__(self, build_id: str = DEFAULT_BUILD) -> None:
        self.build_id = os.getenv("GW_BASELINE_BUILD", build_id)
        self._retriever: AgenticRetriever | None = None
        self._classifier: AgentCostClassifier | None = None

    def supported_conditions(self) -> list[EvidenceCondition]:
        return [EvidenceCondition.SENTENCE_ONLY, EvidenceCondition.LOCAL,
                EvidenceCondition.SAME_REPORT_RRF, EvidenceCondition.CROSS_YEAR_RRF,
                EvidenceCondition.CROSS_YEAR_AGENTIC, EvidenceCondition.COMPANY_AGENTIC,
                EvidenceCondition.PROMISE_WINDOW]

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
