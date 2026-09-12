"""BM25 + dense + RRF + reranker baseline. M0 stub: registers, supports nothing yet."""

from __future__ import annotations

from gw_common.interfaces import BaseSystem
from gw_common.schemas import EvidenceCondition


class BaselineRagSystem(BaseSystem):
    name = "baseline-rag"

    def supported_conditions(self) -> list[EvidenceCondition]:
        # M3 will add LOCAL / SAME_REPORT_RRF / CROSS_YEAR_RRF once the index exists.
        return []


def build_system() -> BaselineRagSystem:
    return BaselineRagSystem()
