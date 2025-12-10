from __future__ import annotations

from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Deque, DefaultDict, Dict, Iterable, List, Optional
import json

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool as psycopg2_pool
except ImportError:  # pragma: no cover - optional dependency
    psycopg2 = None  # type: ignore
    psycopg2_extras = None  # type: ignore
    psycopg2_pool = None  # type: ignore

from streams.models import EventRecord, StreamType


class InMemoryEventStore:
    """Temporary buffer for incoming events with bounded per-key retention."""

    def __init__(self, max_per_key: int = 1000):
        self.max_per_key = max_per_key
        self._events: DefaultDict[str, Deque[EventRecord]] = defaultdict(
            lambda: deque(maxlen=self.max_per_key)
        )

    @staticmethod
    def _key(participant_id: str, stream_type: StreamType) -> str:
        return f"{participant_id}:{stream_type}"

    def append(self, record: EventRecord) -> None:
        key = self._key(record.event.participant_id, record.event.stream_type)
        self._events[key].append(record)

    def list(
        self,
        participant_id: str,
        stream_type: Optional[StreamType] = None,
        limit: int = 100,
    ) -> List[EventRecord]:
        if stream_type is not None:
            records = list(self._events.get(self._key(participant_id, stream_type), []))
        else:
            records = []
            for key, recs in self._events.items():
                if key.startswith(f"{participant_id}:"):
                    records.extend(recs)
        return sorted(records, key=lambda r: r.aligned_timestamp)[-limit:]

    def latest(
        self,
        participant_id: str,
        stream_type: Optional[StreamType] = None,
    ) -> Optional[EventRecord]:
        records = self.list(participant_id, stream_type=stream_type, limit=1)
        return records[-1] if records else None

    def all_records(self) -> Iterable[EventRecord]:
        for records in self._events.values():
            for record in records:
                yield record


class PostgresEventStore:
    """Simple Postgres/Timescale-backed event store for durability."""

    def __init__(self, dsn: str, table: str = "events", create_table: bool = True, minconn: int = 1, maxconn: int = 5):
        if psycopg2 is None or psycopg2_pool is None:
            raise ImportError("psycopg2-binary is required for PostgresEventStore")
        self.dsn = dsn
        self.table = table
        self._pool = psycopg2_pool.SimpleConnectionPool(minconn, maxconn, dsn)
        if create_table:
            self._ensure_table()

    @contextmanager
    def _connection(self):
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()

    def _ensure_table(self) -> None:
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {self.table} (
            event_id TEXT PRIMARY KEY,
            participant_id TEXT NOT NULL,
            stream_type TEXT NOT NULL,
            aligned_timestamp TIMESTAMPTZ NOT NULL,
            received_at TIMESTAMPTZ NOT NULL,
            record JSONB NOT NULL
        );
        """
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(ddl)
            conn.commit()

    @staticmethod
    def _record_to_row(record: EventRecord) -> Dict[str, object]:
        return {
            "event_id": record.event.event_id,
            "participant_id": record.event.participant_id,
            "stream_type": record.event.stream_type,
            "aligned_timestamp": record.aligned_timestamp,
            "received_at": record.received_at,
            "record": json.loads(record.model_dump_json()),
        }

    def append(self, record: EventRecord) -> None:
        row = self._record_to_row(record)
        sql = f"""
        INSERT INTO {self.table} (event_id, participant_id, stream_type, aligned_timestamp, received_at, record)
        VALUES (%(event_id)s, %(participant_id)s, %(stream_type)s, %(aligned_timestamp)s, %(received_at)s, %(record)s)
        ON CONFLICT (event_id) DO NOTHING;
        """
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(sql, row)
            conn.commit()

    def list(
        self,
        participant_id: str,
        stream_type: Optional[StreamType] = None,
        limit: int = 100,
    ) -> List[EventRecord]:
        query = f"""
        SELECT record
        FROM {self.table}
        WHERE participant_id = %(participant_id)s
        """
        params: Dict[str, object] = {"participant_id": participant_id}
        if stream_type is not None:
            query += " AND stream_type = %(stream_type)s"
            params["stream_type"] = stream_type.value if hasattr(stream_type, "value") else str(stream_type)
        query += " ORDER BY aligned_timestamp DESC LIMIT %(limit)s"
        params["limit"] = limit
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [EventRecord.model_validate(r[0]) for r in rows]

    def latest(
        self,
        participant_id: str,
        stream_type: Optional[StreamType] = None,
    ) -> Optional[EventRecord]:
        records = self.list(participant_id, stream_type=stream_type, limit=1)
        return records[0] if records else None

    def all_records(self) -> Iterable[EventRecord]:
        query = f"SELECT record FROM {self.table} ORDER BY aligned_timestamp"
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(query)
            for row in cur.fetchall():
                yield EventRecord.model_validate(row[0])
