from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel

from schemas.telemetry import (
    DecisionCyclePayload,
    MpgDeltaPayload,
    MpgEdge,
    MpgNode,
    MpgSegment,
    MufsEventPayload,
    NoeticStatePayload,
    RogueVariableEventPayload,
    SomaticStatePayload,
    SymbolicStatePayload,
    TelemetryEnvelope,
)


class SessionSummary(BaseModel):
    session_id: str
    experiment_id: str
    subject_id: str
    status: str
    started_utc: str
    ended_utc: Optional[str] = None


class MpgLevelSummary(BaseModel):
    level: int
    node_count: int
    segment_count: int


class MpgSubgraphResponse(BaseModel):
    mpg_id: str
    level: int
    center_node_id: Optional[str] = None
    nodes: List[MpgNode]
    edges: List[MpgEdge]
    segments: List[MpgSegment]


class SnapshotMpg(BaseModel):
    mpg_id: str
    level_summaries: List[MpgLevelSummary]
    base_subgraph: MpgSubgraphResponse


class SnapshotResponse(BaseModel):
    session_id: str
    t_rel_ms: int
    somatic: SomaticStatePayload
    symbolic: SymbolicStatePayload
    noetic: NoeticStatePayload
    last_decision_cycle: Optional[DecisionCyclePayload] = None
    mpg: SnapshotMpg


class ReplayResponse(BaseModel):
    session_id: str
    from_ms: int
    to_ms: int
    messages: List[TelemetryEnvelope[Any]]


class DecisionTraceResponse(BaseModel):
    session_id: str
    decision_id: str
    phases: List[DecisionCyclePayload]
    mufs_events: List[MufsEventPayload] = []
    rogue_variable_events: List[RogueVariableEventPayload] = []
    mpg_full: Optional[MpgSubgraphResponse] = None
    mpg_without_mufs: Optional[MpgSubgraphResponse] = None


# Cohorts / lessons

class Cohort(BaseModel):
    cohort_id: str
    name: str
    description: Optional[str] = None
    member_sessions: List[str]
    created_utc: str


class NoeticSample(BaseModel):
    t_rel_ms: int
    global_coherence_score: float
    entropy_change: float
    band_strengths: List[float] = []


class SubjectNoeticSeries(BaseModel):
    id: str
    subject_label: str
    samples: List[NoeticSample]


class GroupNoeticSample(BaseModel):
    t_rel_ms: int
    mean_global_coherence: float
    dispersion_global_coherence: float
    band_sync_index: List[float] = []


class CohortNoeticSummary(BaseModel):
    cohort_id: str
    members: List[SubjectNoeticSeries]
    group: List[GroupNoeticSample]


class MpgEchoMember(BaseModel):
    session_id: str
    segment_id: str


class MpgEchoWindow(BaseModel):
    trial_id: Optional[str] = None
    t_rel_ms_start: int
    t_rel_ms_end: int


class MpgEchoGroup(BaseModel):
    echo_id: str
    label: Optional[str] = None
    member_segments: List[MpgEchoMember] = []
    consistency_score: float = 0.0
    occurrence_windows: List[MpgEchoWindow] = []


class CohortMpgEchoResponse(BaseModel):
    cohort_id: str
    echoes: List[MpgEchoGroup]
