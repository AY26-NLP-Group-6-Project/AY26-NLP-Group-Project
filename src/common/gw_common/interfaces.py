"""Protocols a system must satisfy to be evaluated or served.

A system implements what it can and returns None for the rest; the harness reports `n/a`
instead of failing. Nothing here imports a system, and no system imports another.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from gw_common.schemas import (
    EvalItem,
    EvidenceCondition,
    EvidenceSpan,
    Prediction,
    Query,
    Trajectory,
)

if TYPE_CHECKING:  # keep FastAPI out of the import path of the eval harness
    from fastapi import APIRouter


@runtime_checkable
class Retriever(Protocol):
    def retrieve(self, query: Query, *, k: int = 10) -> list[EvidenceSpan]:
        """Return at most k evidence spans honouring the filters carried by `query`."""


@runtime_checkable
class ActionClassifier(Protocol):
    def classify(
        self,
        items: Sequence[EvalItem],
        *,
        condition: EvidenceCondition,
        evidence: Mapping[str, list[EvidenceSpan]] | None = None,
    ) -> list[Prediction]:
        """One prediction per item, in the same order."""


@runtime_checkable
class TrajectoryBuilder(Protocol):
    def trajectory(self, company: str, aspect: str, years: range) -> Trajectory: ...


@runtime_checkable
class System(Protocol):
    name: str

    def supported_conditions(self) -> list[EvidenceCondition]: ...

    def retriever(self) -> Retriever | None: ...

    def classifier(self) -> ActionClassifier | None: ...

    def trajectories(self) -> TrajectoryBuilder | None: ...

    def router(self) -> APIRouter | None: ...


class BaseSystem:
    """Convenience base: subclass and override only what the system supports."""

    name: str = "unnamed"

    def supported_conditions(self) -> list[EvidenceCondition]:
        return [EvidenceCondition.SENTENCE_ONLY]

    def retriever(self) -> Retriever | None:
        return None

    def classifier(self) -> ActionClassifier | None:
        return None

    def trajectories(self) -> TrajectoryBuilder | None:
        return None

    def router(self) -> APIRouter | None:
        return None
