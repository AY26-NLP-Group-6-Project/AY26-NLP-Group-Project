"""Temporal claim graph system. M0 stub: registers and declares its future conditions."""

from __future__ import annotations

from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvidenceCondition


class GraphRagSystem(BaseSystem):
    name = "graph-rag"

    def supported_conditions(self) -> list[EvidenceCondition]:
        # M4 will add CROSS_YEAR_GRAPH and CROSS_YEAR_FUSED once the graph is built.
        return []


def build_system() -> GraphRagSystem:
    return GraphRagSystem()
