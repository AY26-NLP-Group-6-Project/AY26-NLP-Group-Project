"""Bounded traversal policy (M7). Registered as its own system so it is compared, not assumed."""

from __future__ import annotations

from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvidenceCondition

MAX_HOPS = 3
TIMEOUT_S = 8.0


class AgenticGraphRagSystem(BaseSystem):
    name = "agentic-graph-rag"

    def supported_conditions(self) -> list[EvidenceCondition]:
        # M7: CROSS_YEAR_AGENTIC. The agent plans and rewrites; the reranker still picks
        # (arXiv 2601.07711 finds agents worse than a reranker at final document selection).
        return []


def build_system() -> AgenticGraphRagSystem:
    return AgenticGraphRagSystem()
