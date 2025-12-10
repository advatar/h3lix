from __future__ import annotations

from typing import Iterable, List, Optional

from typing import Protocol

from brain.layout import build_graph_snapshot
from brain.models import BrainSnapshot
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from streams.models import EventRecord


class EventStore(Protocol):
    def list(self, participant_id: str, stream_type: object | None = None, limit: int = 100) -> list[EventRecord]:
        ...

    def all_records(self) -> Iterable[EventRecord]:
        ...


class BrainViewService:
    """Builds visualization-ready snapshots of the brain state."""

    def __init__(
        self,
        repo: Neo4jMPGRepository | InMemoryMPGRepository,
        store: EventStore,
    ):
        self.repo = repo
        self.store = store

    def snapshot(
        self,
        participant_id: Optional[str] = None,
        level: Optional[int] = None,
        event_limit: int = 50,
    ) -> BrainSnapshot:
        graph = self.repo.get_graph(level=level)
        graph_snapshot = build_graph_snapshot(graph, level=level)
        events = self._recent_events(participant_id, limit=event_limit)
        return BrainSnapshot(graph=graph_snapshot, recent_events=events)

    def _recent_events(self, participant_id: Optional[str], limit: int) -> List[EventRecord]:
        if participant_id:
            return self.store.list(participant_id, limit=limit)
        records = sorted(self.store.all_records(), key=lambda r: r.aligned_timestamp)
        return records[-limit:]
