from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from streams.models import EventReceipt, EventRecord


class Position(BaseModel):
    x: float
    y: float
    z: float


class VisualNode(BaseModel):
    id: str
    name: str
    level: int = 0
    importance: float = 0.0
    confidence: float = 0.0
    labels: List[str] = Field(default_factory=list)
    position: Position = Field(default_factory=lambda: Position(x=0.0, y=0.0, z=0.0))
    color: str = "#33a1fd"
    size: float = 1.0
    valence: Optional[float] = None


class VisualEdge(BaseModel):
    src: str
    dst: str
    rel_type: str
    strength: float = 0.0
    confidence: float = 0.0
    color: str = "#999999"


class GraphSnapshot(BaseModel):
    level: Optional[int] = None
    layout: str = "spring"
    nodes: List[VisualNode] = Field(default_factory=list)
    edges: List[VisualEdge] = Field(default_factory=list)


class StreamUpdate(BaseModel):
    """Lightweight update for live streams."""

    receipt: EventReceipt
    metrics: Dict[str, Any] = Field(default_factory=dict)


class BrainSnapshot(BaseModel):
    graph: GraphSnapshot
    recent_events: List[EventRecord] = Field(default_factory=list)


class BrainEvent(BaseModel):
    """Message sent over the live brain stream."""

    kind: Literal["stream_event", "graph_snapshot", "qrv_event"]
    stream: Optional[StreamUpdate] = None
    graph: Optional[GraphSnapshot] = None
    snapshot: Optional[BrainSnapshot] = None
    qrv: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
