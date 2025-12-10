from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar

from pydantic import BaseModel, Field
from typing_extensions import Literal


class MessageType(str, Enum):
    SOMATIC_STATE = "somatic_state"
    SYMBOLIC_STATE = "symbolic_state"
    NOETIC_STATE = "noetic_state"
    DECISION_CYCLE = "decision_cycle"
    MPG_DELTA = "mpg_delta"
    ROGUE_VARIABLE_EVENT = "rogue_variable_event"
    MUFS_EVENT = "mufs_event"


class SourceLayer(str, Enum):
    SOMATIC = "Somatic"
    SYMBOLIC = "Symbolic"
    NOETIC = "Noetic"
    MIRROR_CORE = "MirrorCore"
    MPG = "MPG"


class StreamName(str, Enum):
    SOMATIC = "somatic"
    SYMBOLIC = "symbolic"
    BEHAVIORAL = "behavioral"
    EXTERNAL = "external"


class UnawarenessType(str, Enum):
    INPUT = "IU"
    PROCESS = "PU"


class SomaticAnticipatoryMarker(BaseModel):
    marker_type: Literal["readiness_like", "phase_locking", "other"]
    lead_time_ms: int
    confidence: float = Field(ge=0.0, le=1.0)


class SomaticStatePayload(BaseModel):
    t_rel_ms: int
    window_ms: int
    features: Dict[str, float]
    innovation: Optional[Dict[str, float]] = None
    covariance_diag: Optional[Dict[str, float]] = None
    global_uncertainty_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    change_point: bool = False
    anomaly_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    anticipatory_markers: List[SomaticAnticipatoryMarker] = Field(default_factory=list)


class SymbolicBelief(BaseModel):
    id: str
    kind: Literal["entity", "event", "relation", "policy"]
    label: str
    description: Optional[str] = None
    valence: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    intensity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    recency: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)


class SymbolicPredictionOption(BaseModel):
    value: str
    probability: float = Field(ge=0.0, le=1.0)


class SymbolicPrediction(BaseModel):
    id: str
    target_type: Literal["word", "event", "outcome"]
    horizon_ms: Optional[int] = None
    topk: List[SymbolicPredictionOption]
    brier_score: Optional[float] = None
    realized_value: Optional[str] = None
    realized_error: Optional[float] = None


class SymbolicUncertaintyRegion(BaseModel):
    label: str
    belief_ids: List[str]
    comment: Optional[str] = None


class SymbolicStatePayload(BaseModel):
    t_rel_ms: int
    belief_revision_id: str
    beliefs: List[SymbolicBelief]
    predictions: List[SymbolicPrediction] = Field(default_factory=list)
    uncertainty_regions: List[SymbolicUncertaintyRegion] = Field(default_factory=list)


class NoeticStreamCorrelation(BaseModel):
    stream_x: StreamName
    stream_y: StreamName
    r: float = Field(ge=-1.0, le=1.0)


class NoeticSpectrumBand(BaseModel):
    band_label: str
    freq_range_hz: Tuple[float, float]
    coherence_strength: float = Field(ge=0.0, le=1.0)


class NoeticIntuitiveAccuracyEstimate(BaseModel):
    p_better_than_baseline: float = Field(ge=0.0, le=1.0)
    calibration_error: Optional[float] = None


class NoeticStatePayload(BaseModel):
    t_rel_ms: int
    window_ms: int
    global_coherence_score: float = Field(ge=0.0, le=1.0)
    entropy_change: float
    stream_correlations: List[NoeticStreamCorrelation]
    coherence_spectrum: List[NoeticSpectrumBand]
    intuitive_accuracy_estimate: Optional[NoeticIntuitiveAccuracyEstimate] = None


class DecisionAction(BaseModel):
    action_id: str
    label: str
    params: Optional[Dict[str, Any]] = None


class DecisionOutcome(BaseModel):
    label: str
    metrics: Dict[str, float]


class NoeticAdjustment(BaseModel):
    attention_gain: Optional[float] = None
    decision_threshold_delta: Optional[float] = None
    learning_rate_delta: Optional[float] = None


class DecisionCyclePayload(BaseModel):
    sork_cycle_id: str
    decision_id: Optional[str] = None
    phase: Literal["S", "O", "R", "K", "N", "S_prime"]
    phase_started_utc: datetime
    phase_ended_utc: Optional[datetime] = None
    stimulus_refs: Optional[List[Dict[str, str]]] = None
    organism_belief_ids: Optional[List[str]] = None
    response_action: Optional[DecisionAction] = None
    consequence_outcome: Optional[DecisionOutcome] = None
    noetic_adjustments: Optional[NoeticAdjustment] = None


class MpgEvidencePreview(BaseModel):
    evidence_id: str
    snippet: str
    source_class: str
    timestamp_utc: datetime


class MpgNodeMetrics(BaseModel):
    valence: float = Field(ge=-1.0, le=1.0)
    intensity: float = Field(ge=0.0, le=1.0)
    recency: float = Field(ge=0.0, le=1.0)
    stability: float = Field(ge=0.0, le=1.0)


class MpgNode(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    layer_tags: List[str] = Field(default_factory=list)
    metrics: MpgNodeMetrics
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    roles: List[str] = Field(default_factory=list)
    evidence_preview: List[MpgEvidencePreview] = Field(default_factory=list)
    reasoning_provenance: Optional[str] = None


class MpgEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    strength: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class MpgSegment(BaseModel):
    id: str
    label: str
    level: int
    member_node_ids: List[str]
    cohesion: float = Field(ge=0.0, le=1.0)
    average_importance: float = Field(ge=0.0, le=1.0)
    average_confidence: float = Field(ge=0.0, le=1.0)
    affective_load: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class MpgOperation(BaseModel):
    kind: Literal["add_node", "update_node", "add_edge", "update_edge", "add_segment", "update_segment"]
    node: Optional[MpgNode] = None
    node_id: Optional[str] = None
    edge: Optional[MpgEdge] = None
    edge_id: Optional[str] = None
    segment: Optional[MpgSegment] = None
    segment_id: Optional[str] = None
    patch: Optional[Dict[str, Any]] = None


class MpgDeltaPayload(BaseModel):
    mpg_id: str
    level: int
    delta_id: str
    operations: List[MpgOperation]


class RogueVariableImpactFactors(BaseModel):
    rate_of_change: float = Field(ge=0.0, le=1.0)
    breadth_of_impact: float = Field(ge=0.0, le=1.0)
    amplification: float = Field(ge=0.0, le=1.0)
    emotional_load: float = Field(ge=0.0, le=1.0)
    gate_leverage: float = Field(ge=0.0, le=1.0)
    robustness: float = Field(ge=0.0, le=1.0)


class RogueVariableShapleyStats(BaseModel):
    mean_abs_contrib: float
    std_abs_contrib: float
    candidate_abs_contrib: float
    z_score: float


class RogueVariableEventPayload(BaseModel):
    rogue_id: str
    mpg_id: str
    candidate_type: Literal["segment", "pathway"]
    level_range: Tuple[int, int]
    segment_ids: Optional[List[str]] = None
    pathway_nodes: Optional[List[str]] = None
    shapley_stats: RogueVariableShapleyStats
    potency_index: float
    impact_factors: RogueVariableImpactFactors


class DecisionUtility(BaseModel):
    choice: str
    utility: Dict[str, float]


class MufsEventPayload(BaseModel):
    mufs_id: str
    decision_id: str
    mpg_id: str
    unawareness_types: List[UnawarenessType]
    input_unaware_refs: Optional[List[str]] = None
    process_unaware_node_ids: Optional[List[str]] = None
    decision_full: DecisionUtility
    decision_without_U: DecisionUtility
    minimal: bool
    search_metadata: Optional[Dict[str, Any]] = None


PayloadT = TypeVar(
    "PayloadT",
    SomaticStatePayload,
    SymbolicStatePayload,
    NoeticStatePayload,
    DecisionCyclePayload,
    MpgDeltaPayload,
    RogueVariableEventPayload,
    MufsEventPayload,
)


class TelemetryEnvelope(BaseModel, Generic[PayloadT]):
    v: Literal["1"] = "1"
    message_type: MessageType
    timestamp_utc: datetime
    experiment_id: str
    session_id: str
    subject_id: str
    run_id: Optional[str] = None
    sork_cycle_id: Optional[str] = None
    decision_id: Optional[str] = None
    source_layer: SourceLayer
    sequence: int
    payload: PayloadT
