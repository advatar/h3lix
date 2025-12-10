from __future__ import annotations

import uuid
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class QMSState(BaseModel):
    class Config:
        arbitrary_types_allowed = True
    basis: List[str]
    amplitudes: List[complex]
    session_id: Optional[str] = None
    t_rel_ms: Optional[float] = None
    norm: float = 0.0
    meta: Dict[str, object] = Field(default_factory=dict)

    def as_vector(self) -> List[complex]:
        return self.amplitudes


class RogueDirection(BaseModel):
    direction_id: str
    eigenvalue: float
    loadings: Dict[str, float]
    high_segments: List[str]
    delta_error: float


class RogueDetectionResult(BaseModel):
    triggered: bool
    error_norm: float
    ablation_improvement: float
    rogue_directions: List[RogueDirection] = Field(default_factory=list)
    rogue_segments: List[str] = Field(default_factory=list)
    event_id: Optional[str] = None
    pre_state: Optional[QMSState] = None
    post_state: Optional[QMSState] = None


class RogueEventRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    t_rel_ms: float
    detection: RogueDetectionResult
    prompt_id: Optional[str] = None


class HILDState(str, Enum):
    idle = "Idle"
    pending = "PendingRogue"
    clarifying = "Clarifying"
    passive_safe = "PassiveSafe"
    resolved = "Resolved"


class HILDPrompt(BaseModel):
    prompt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    anchor: str
    ambiguity: str
    request: str

    @property
    def text(self) -> str:
        return f"{self.anchor} {self.ambiguity} {self.request}"


class HILDStatus(BaseModel):
    session_id: str
    state: HILDState = HILDState.idle
    active_event_id: Optional[str] = None
    prompt: Optional[HILDPrompt] = None
    last_transition_ms: Optional[float] = None
