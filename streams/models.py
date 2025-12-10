from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field, field_validator


class StreamType(str, Enum):
    somatic = "somatic"
    text = "text"
    audio = "audio"
    video = "video"
    meta = "meta"
    task = "task"


class EventQuality(BaseModel):
    sampling_rate_hz: Optional[float] = None
    signal_to_noise: Optional[float] = None
    completeness: Optional[float] = Field(None, ge=0.0, le=1.0)
    battery_level: Optional[float] = Field(None, ge=0.0, le=1.0)


class EventEnvelope(BaseModel):
    """Unified envelope for all human data streams."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    source: str
    stream_type: StreamType
    timestamp_utc: datetime
    device_clock: Optional[float] = Field(default=None, alias="local_device_clock")
    session_id: Optional[str] = None
    scope: Optional[str] = None
    segments: Optional[List[str]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    quality: Optional[EventQuality] = None

    model_config = {"populate_by_name": True}

    @field_validator("timestamp_utc", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: Any) -> Any:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        return value


class EventBatch(BaseModel):
    events: List[EventEnvelope] = Field(default_factory=list)


class AlignmentMetadata(BaseModel):
    aligned_timestamp: datetime
    clock_offset_s: float = 0.0
    drift_ppm: float = 0.0
    source: str
    participant_id: str


class EventRecord(BaseModel):
    event: EventEnvelope
    aligned_timestamp: datetime
    received_at: datetime
    clock_offset_s: float = 0.0
    drift_ppm: float = 0.0


class EventReceipt(BaseModel):
    event_id: str
    participant_id: str
    source: str
    stream_type: StreamType
    aligned_timestamp: datetime
    clock_offset_s: float
    drift_ppm: float
    received_at: datetime

    @classmethod
    def from_record(cls, record: EventRecord) -> "EventReceipt":
        return cls(
            event_id=record.event.event_id,
            participant_id=record.event.participant_id,
            source=record.event.source,
            stream_type=record.event.stream_type,
            aligned_timestamp=record.aligned_timestamp,
            clock_offset_s=record.clock_offset_s,
            drift_ppm=record.drift_ppm,
            received_at=record.received_at,
        )


class BatchIngestResponse(BaseModel):
    ingested: List[EventReceipt]
