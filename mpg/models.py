from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    id: str
    description: str
    source_type: str
    pointer: str
    snippet: str
    timestamp: float
    c: float
    q: float
    u: float
    t: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MPGNode(BaseModel):
    id: str
    name: str
    layers: List[str]
    valence: float = Field(..., ge=-1.0, le=1.0)
    intensity: float = Field(..., ge=0.0, le=1.0)
    recency: float = Field(..., ge=0.0, le=1.0)
    stability: float = Field(..., ge=0.0, le=1.0)
    importance: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    level: int
    visible: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MPGEdge(BaseModel):
    src: str
    dst: str
    rel_type: str
    strength: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SegmentState(BaseModel):
    id: str
    segment_id: str
    t: float
    rv: Optional[bool] = None
    rv_score: Optional[float] = None
    coherence: Optional[float] = None
    potency: Optional[float] = None
    somatic_arousal: Optional[float] = None
    innovation: Optional[float] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
