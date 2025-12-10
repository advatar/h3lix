from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Tuple

from streams.models import AlignmentMetadata, EventEnvelope


@dataclass
class ClockState:
    offset: float
    last_device_clock: float
    drift_ppm: float
    updated_at: float


class TimeAligner:
    """Tracks per-device clock offsets and projects device clocks into master UTC."""

    def __init__(self, smoothing: float = 0.1):
        self.smoothing = smoothing
        self._clocks: Dict[str, ClockState] = {}

    @staticmethod
    def _key(event: EventEnvelope) -> str:
        return f"{event.participant_id}:{event.source}"

    def align(self, event: EventEnvelope) -> Tuple[datetime, AlignmentMetadata]:
        now_mono = time.monotonic()
        key = self._key(event)

        if event.device_clock is None:
            aligned = event.timestamp_utc
            meta = AlignmentMetadata(
                aligned_timestamp=aligned,
                clock_offset_s=0.0,
                drift_ppm=0.0,
                source=event.source,
                participant_id=event.participant_id,
            )
            return aligned, meta

        measured_offset = event.timestamp_utc.timestamp() - event.device_clock
        prev = self._clocks.get(key)

        if prev is None:
            state = ClockState(offset=measured_offset, last_device_clock=event.device_clock, drift_ppm=0.0, updated_at=now_mono)
        else:
            delta_clock = event.device_clock - prev.last_device_clock
            delta_offset = measured_offset - prev.offset
            drift_ppm = ((delta_offset) / max(delta_clock, 1e-6)) * 1e6 if delta_clock else 0.0
            smoothed_offset = prev.offset * (1 - self.smoothing) + measured_offset * self.smoothing
            state = ClockState(offset=smoothed_offset, last_device_clock=event.device_clock, drift_ppm=drift_ppm, updated_at=now_mono)

        self._clocks[key] = state
        aligned_seconds = event.device_clock + state.offset
        aligned = datetime.fromtimestamp(aligned_seconds, tz=timezone.utc)

        meta = AlignmentMetadata(
            aligned_timestamp=aligned,
            clock_offset_s=state.offset,
            drift_ppm=state.drift_ppm,
            source=event.source,
            participant_id=event.participant_id,
        )
        return aligned, meta
