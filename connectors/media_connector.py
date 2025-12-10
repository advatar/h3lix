from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from streams.models import EventEnvelope, StreamType


@dataclass
class MediaPayload:
    participant_id: str
    uri: str
    duration_ms: int
    session_id: Optional[str] = None
    experiment_tag: Optional[str] = None
    source: str = "media_upload"
    media_type: str = "audio"  # "audio" | "video"


def media_event(meta: MediaPayload) -> EventEnvelope:
    payload: Dict = {
        "uri": meta.uri,
        "duration_ms": meta.duration_ms,
        "session_id": meta.session_id,
        "experiment_tag": meta.experiment_tag,
    }
    stream = StreamType.audio if meta.media_type == "audio" else StreamType.video
    return EventEnvelope(
        participant_id=meta.participant_id,
        source=meta.source,
        stream_type=stream,
        timestamp_utc=0.0,
        payload=payload,
        scope="media",
    )
