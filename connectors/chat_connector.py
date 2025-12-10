from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from streams.models import EventEnvelope, StreamType

ParticipantLookup = Callable[[str], Optional[str]]


@dataclass
class ChatMessage:
    message_id: str
    channel: str
    user: str
    text: str
    thread_ts: Optional[str]
    timestamp_utc: float


class ChatConnector:
    """Maps chat messages (Slack/Discord) to EventEnvelope."""

    def __init__(self, participant_lookup: ParticipantLookup):
        self.participant_lookup = participant_lookup

    def to_event(self, msg: ChatMessage) -> Optional[EventEnvelope]:
        participant_id = self.participant_lookup(msg.user)
        if not participant_id:
            return None
        payload: Dict = {
            "message_id": msg.message_id,
            "channel": msg.channel,
            "text": msg.text,
            "thread_ts": msg.thread_ts,
        }
        return EventEnvelope(
            participant_id=participant_id,
            source="slack",
            stream_type=StreamType.text,
            timestamp_utc=msg.timestamp_utc,
            payload=payload,
            scope="chat",
        )
