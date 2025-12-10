from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from streams.models import EventEnvelope, StreamType

ParticipantLookup = Callable[[str], Optional[str]]


@dataclass
class CalendarEvent:
    event_id: str
    title: str
    start_utc: float
    end_utc: float
    organizer: str
    attendees: list[str]
    location: Optional[str] = None
    description: Optional[str] = None


class CalendarConnector:
    """Maps calendar items to contextual EventEnvelope entries."""

    def __init__(self, participant_lookup: ParticipantLookup):
        self.participant_lookup = participant_lookup

    def to_event(self, item: CalendarEvent) -> Optional[EventEnvelope]:
        participant_id = self.participant_lookup(item.organizer)
        if not participant_id:
            return None
        payload: Dict = {
            "event_id": item.event_id,
            "title": item.title,
            "start_utc": item.start_utc,
            "end_utc": item.end_utc,
            "attendees": item.attendees,
            "location": item.location,
            "description": (item.description or "")[:240],
        }
        return EventEnvelope(
            participant_id=participant_id,
            source="calendar",
            stream_type=StreamType.meta,
            timestamp_utc=item.start_utc,
            payload=payload,
            scope="calendar",
        )
