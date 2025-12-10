from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class SomaticSample(BaseModel):
    user_id: str
    trial_id: str
    timestamp: float  # global time reference
    channel: str      # e.g. "HR", "EDA", "PUPIL"
    value: float


class Trial(BaseModel):
    id: str
    user_id: str
    session_id: str
    stimulus_onset: float
    decision_time: float
    outcome: float  # reward, correctness, etc.


class BeliefState(BaseModel):
    trial_id: str
    hypotheses: Dict[str, float]  # e.g. {"H0": 0.6, "H1": 0.4}
    uncertainty: float = Field(..., ge=0.0)
    supporting_nodes: List[str]
