"""Two reference systems that ship with the harness.

`majority` is the sanity floor every other system must beat. Neither sees gold labels: the constant
label is a fixed prior written in config, not something read off the evaluation set.
"""

from __future__ import annotations

import random
import time
from collections.abc import Mapping, Sequence

from gw_common.interfaces import ActionClassifier, BaseSystem
from gw_common.schemas import (
    ALL_LABELS,
    EvalItem,
    EvidenceCondition,
    EvidenceSpan,
    Label,
    Prediction,
)


class ConstantClassifier:
    def __init__(self, label: Label = Label.IMPLEMENTED) -> None:
        self.label = label

    def classify(
        self,
        items: Sequence[EvalItem],
        *,
        condition: EvidenceCondition,
        evidence: Mapping[str, list[EvidenceSpan]] | None = None,
    ) -> list[Prediction]:
        out = []
        for it in items:
            t0 = time.perf_counter()
            out.append(
                Prediction(
                    item_id=it.item_id,
                    label=self.label,
                    scores={lab.value: float(lab == self.label) for lab in ALL_LABELS},
                    latency_ms=(time.perf_counter() - t0) * 1000,
                )
            )
        return out


class RandomClassifier:
    def __init__(self, seed: int = 20260912) -> None:
        self.rng = random.Random(seed)

    def classify(
        self,
        items: Sequence[EvalItem],
        *,
        condition: EvidenceCondition,
        evidence: Mapping[str, list[EvidenceSpan]] | None = None,
    ) -> list[Prediction]:
        out = []
        for it in items:
            t0 = time.perf_counter()
            lab = self.rng.choice(ALL_LABELS)
            out.append(
                Prediction(item_id=it.item_id, label=lab, latency_ms=(time.perf_counter() - t0) * 1000)
            )
        return out


class MajoritySystem(BaseSystem):
    name = "majority"

    def __init__(self, label: Label = Label.IMPLEMENTED) -> None:
        self._clf = ConstantClassifier(label)

    def supported_conditions(self) -> list[EvidenceCondition]:
        return [EvidenceCondition.SENTENCE_ONLY]

    def classifier(self) -> ActionClassifier | None:
        return self._clf


class RandomSystem(BaseSystem):
    name = "random"

    def __init__(self, seed: int = 20260912) -> None:
        self._clf = RandomClassifier(seed)

    def supported_conditions(self) -> list[EvidenceCondition]:
        return [EvidenceCondition.SENTENCE_ONLY]

    def classifier(self) -> ActionClassifier | None:
        return self._clf


def build_majority() -> MajoritySystem:
    return MajoritySystem()


def build_random() -> RandomSystem:
    return RandomSystem()
