from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TelemetryEnvelope(BaseModel):
    v: Literal["1"] = "1"
    message_type: Literal[
        "somatic_state",
        "symbolic_state",
        "noetic_state",
        "decision_cycle",
        "mpg_delta",
        "rogue_variable_event",
        "mufs_event",
    ]
    timestamp_utc: str
    experiment_id: str = "unknown"
    session_id: str
    subject_id: str
    run_id: Optional[str] = None
    sork_cycle_id: Optional[str] = None
    decision_id: Optional[str] = None
    source_layer: Literal["Somatic", "Symbolic", "Noetic", "MirrorCore", "MPG"]
    sequence: int = 0
    payload: Dict[str, Any]


class SomaticStatePayload(BaseModel):
    t_rel_ms: int = 0
    window_ms: int = 0
    features: Dict[str, float] = Field(default_factory=dict)
    innovation: Optional[Dict[str, float]] = None
    covariance_diag: Optional[Dict[str, float]] = None
    global_uncertainty_score: Optional[float] = None
    change_point: bool = False
    anomaly_score: Optional[float] = None
    anticipatory_markers: Optional[List[Dict[str, Any]]] = None


class SymbolicStatePayload(BaseModel):
    t_rel_ms: int = 0
    belief_revision_id: str = "br0"
    beliefs: List[Dict[str, Any]] = Field(default_factory=list)
    predictions: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty_regions: Optional[List[Dict[str, Any]]] = None


class NoeticStatePayload(BaseModel):
    t_rel_ms: int = 0
    window_ms: int = 0
    global_coherence_score: float = 0.0
    entropy_change: float = 0.0
    stream_correlations: List[Dict[str, Any]] = Field(default_factory=list)
    coherence_spectrum: List[Dict[str, Any]] = Field(default_factory=list)
    intuitive_accuracy_estimate: Optional[Dict[str, float]] = None


class DecisionCyclePayload(BaseModel):
    sork_cycle_id: str
    decision_id: Optional[str] = None
    phase: Literal["S", "O", "R", "K", "N", "S_prime"]
    phase_started_utc: str
    phase_ended_utc: Optional[str] = None
    stimulus_refs: Optional[List[Dict[str, Any]]] = None
    organism_belief_ids: Optional[List[str]] = None
    response_action: Optional[Dict[str, Any]] = None
    consequence_outcome: Optional[Dict[str, Any]] = None
    noetic_adjustments: Optional[Dict[str, Any]] = None


class MpgNode(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    layer_tags: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.0
    importance: float = 0.0
    roles: List[str] = Field(default_factory=list)
    evidence_preview: Optional[List[Dict[str, Any]]] = None
    reasoning_provenance: Optional[str] = None


class MpgEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    strength: float = 0.0
    confidence: float = 0.0


class MpgSegment(BaseModel):
    id: str
    label: str
    level: int
    member_node_ids: List[str]
    cohesion: float = 0.0
    average_importance: float = 0.0
    average_confidence: float = 0.0
    affective_load: Optional[float] = None


class MpgSubgraphResponse(BaseModel):
    mpg_id: str
    level: int
    center_node_id: Optional[str] = None
    nodes: List[MpgNode] = Field(default_factory=list)
    edges: List[MpgEdge] = Field(default_factory=list)
    segments: List[MpgSegment] = Field(default_factory=list)


class SnapshotResponse(BaseModel):
    session_id: str
    t_rel_ms: int
    somatic: SomaticStatePayload
    symbolic: SymbolicStatePayload
    noetic: NoeticStatePayload
    last_decision_cycle: Optional[DecisionCyclePayload] = None
    mpg: Dict[str, Any]


class DecisionTraceResponse(BaseModel):
    session_id: str
    decision_id: str
    phases: List[DecisionCyclePayload] = Field(default_factory=list)
    mufs_events: Optional[List[Dict[str, Any]]] = None
    rogue_variable_events: Optional[List[Dict[str, Any]]] = None
    mpg_full: Optional[MpgSubgraphResponse] = None
    mpg_without_mufs: Optional[MpgSubgraphResponse] = None


class ReplayResponse(BaseModel):
    session_id: str
    from_ms: int
    to_ms: int
    messages: List[TelemetryEnvelope]
