from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from streams.models import EventEnvelope, StreamType


ParticipantLookup = Callable[[str], Optional[str]]


@dataclass
class EmailMessage:
    message_id: str
    thread_id: str
    subject: str
    snippet: str
    folder: str
    direction: str  # "IN" | "OUT"
    from_addr: str
    to_addrs: list[str]
    cc_addrs: list[str]
    timestamp_utc: float


class EmailConnector:
    """Transforms email payloads into EventEnvelopes for ingestion."""

    def __init__(self, participant_lookup: ParticipantLookup):
        self.participant_lookup = participant_lookup

    def to_event(self, msg: EmailMessage) -> Optional[EventEnvelope]:
        participant_id = self.participant_lookup(msg.from_addr)
        if not participant_id:
            return None
        payload: Dict = {
            "message_id": msg.message_id,
            "thread_id": msg.thread_id,
            "subject": msg.subject,
            "snippet": msg.snippet,
            "folder": msg.folder,
            "direction": msg.direction,
            "participants": list({msg.from_addr, *msg.to_addrs, *msg.cc_addrs}),
        }
        return EventEnvelope(
            participant_id=participant_id,
            source="gmail",
            stream_type=StreamType.text,
            timestamp_utc=msg.timestamp_utc,
            payload=payload,
            scope="email",
        )
