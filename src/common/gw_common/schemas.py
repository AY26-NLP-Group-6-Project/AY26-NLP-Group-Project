"""Shared data shapes. Every system, the eval harness and the API use these and nothing else."""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, Field


class Label(StrEnum):
    """The single label set (03-eval-contract.md): three A3CG actions plus `none`."""

    IMPLEMENTED = "implemented"
    PLANNING = "planning"
    INDETERMINATE = "indeterminate"
    NONE = "none"


ACTION_LABELS: tuple[Label, ...] = (Label.IMPLEMENTED, Label.PLANNING, Label.INDETERMINATE)
ALL_LABELS: tuple[Label, ...] = (*ACTION_LABELS, Label.NONE)


class EvidenceCondition(StrEnum):
    SENTENCE_ONLY = "sentence_only"
    LOCAL = "local"
    SAME_REPORT_RRF = "same_report_rrf"
    CROSS_YEAR_RRF = "cross_year_rrf"
    CROSS_YEAR_GRAPH = "cross_year_graph"
    CROSS_YEAR_FUSED = "cross_year_fused"
    CROSS_YEAR_AGENTIC = "cross_year_agentic"


class EvalItem(BaseModel):
    """What a system sees. Never carries the gold label."""

    item_id: str
    text: str
    aspect: str | None = None
    category: str | None = None
    company: str
    sgx_code: str | None = None
    year: int
    page: int | None = None
    file: str | None = None
    context_prev: str = ""
    context_next: str = ""
    pilot: bool = False


class GoldItem(EvalItem):
    gold_label: Label
    label_source: str
    split: str = "dev"  # dev for anything tuned on; test is opened once, for the report
    # Annotation provenance and quality: annotator count, agreement, tie/adjudication, per-model
    # pre-labels, row_type, aspect_source. Slices read it; systems never see it.
    meta: dict[str, object] = Field(default_factory=dict)

    HIDDEN: ClassVar[set[str]] = {"gold_label", "label_source", "split", "meta"}

    def to_eval_item(self) -> EvalItem:
        return EvalItem(**self.model_dump(exclude=self.HIDDEN))


class EvidenceSpan(BaseModel):
    statement_id: str
    text: str
    company: str
    year: int
    page: int | None = None
    file: str | None = None
    score: float = 0.0
    why: str = ""  # bm25 | dense | rrf | graph:follows_up | graph:metric | agent:hop2 …


class Query(BaseModel):
    text: str
    company: str | None = None
    aspect: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    anchor_year: int | None = None  # the year of the statement being classified; cross-year excludes it
    # The sentence being classified. Retrievers must never return it (see gw_common.evidence); kept apart
    # from `text` so a rewritten query does not change what counts as the target.
    target_text: str | None = None
    exclude_statement_ids: list[str] = Field(default_factory=list)  # system-native ids only
    condition: EvidenceCondition = EvidenceCondition.CROSS_YEAR_RRF


class Prediction(BaseModel):
    item_id: str
    label: Label
    scores: dict[str, float] | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    graph_hops: int = 0


class TrajectoryPoint(BaseModel):
    year: int
    label: Label
    statement_id: str | None = None
    page: int | None = None
    metric: dict[str, object] | None = None


class Transition(BaseModel):
    from_year: int
    to_year: int
    kind: str  # planning_to_implemented | stuck_planning | dropped | weakened | new


class Trajectory(BaseModel):
    company: str
    aspect: str
    points: list[TrajectoryPoint] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)


class RunManifest(BaseModel):
    run_id: str
    system: str
    task: str
    conditions: list[EvidenceCondition]
    dataset_id: str
    dataset_hash: str
    label_source: str
    n_items: int
    git_sha: str
    git_dirty: bool
    graph_build_id: str | None = None
    llm: dict[str, object] = Field(default_factory=dict)  # model, effort, temperature, cache (no keys)
    repeats: int = 1
    seed: int = 20260912
    started_at: str
    finished_at: str | None = None
    wall_seconds: float | None = None
    config: dict[str, object] = Field(default_factory=dict)
