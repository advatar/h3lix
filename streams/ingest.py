from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from streams.bus import StreamBus
from streams.consent import ConsentManager, STREAM_SCOPE_MAP
from streams.models import (
    BatchIngestResponse,
    EventBatch,
    EventEnvelope,
    EventReceipt,
    EventRecord,
    StreamType,
)
from streams.processors import NoeticEventProcessor, SomaticEventProcessor, SymbolicEventProcessor
from streams.mpg_sink import MPGSink
from streams.store import InMemoryEventStore
from streams.time_alignment import TimeAligner


class EventIngestService:
    """Aligns, stores, and routes incoming human stream events."""

    def __init__(
        self,
        aligner: TimeAligner,
        store: InMemoryEventStore,
        somatic_processor: Optional[SomaticEventProcessor] = None,
        symbolic_processor: Optional[SymbolicEventProcessor] = None,
        noetic_processor: Optional[NoeticEventProcessor] = None,
        consent_manager: Optional[ConsentManager] = None,
        mpg_sink: Optional[MPGSink] = None,
        bus: Optional[StreamBus] = None,
    ):
        self.aligner = aligner
        self.store = store
        self.somatic_processor = somatic_processor
        self.symbolic_processor = symbolic_processor
        self.noetic_processor = noetic_processor
        self.consent_manager = consent_manager
        self.mpg_sink = mpg_sink
        self.bus = bus

    async def ingest(self, event: EventEnvelope) -> EventRecord:
        scope = event.scope or STREAM_SCOPE_MAP.get(event.stream_type) or event.stream_type.value
        if self.consent_manager:
            self.consent_manager.ensure_allowed(event.participant_id, scope)
        aligned_ts, meta = self.aligner.align(event)
        record = EventRecord(
            event=event,
            aligned_timestamp=aligned_ts,
            received_at=datetime.now(timezone.utc),
            clock_offset_s=meta.clock_offset_s,
            drift_ppm=meta.drift_ppm,
        )
        self.store.append(record)
        results = self._dispatch(event, aligned_ts)
        if self.mpg_sink:
            self.mpg_sink.handle(event, results, aligned_ts=aligned_ts)
        if self.bus:
            receipt = EventReceipt.from_record(record)
            await self.bus.publish(
                {
                    "kind": "stream_event",
                    "stream": {
                        "receipt": receipt.model_dump(mode="json"),
                        "metrics": self._summarize_results(results),
                        "aligned_ts_ms": int(aligned_ts.timestamp() * 1000),
                    },
                    "meta": {
                        "participant_id": event.participant_id,
                        "stream_type": event.stream_type.value,
                        "session_id": event.session_id,
                        "message_type": self._message_type(event),
                        "aligned_ts_ms": int(aligned_ts.timestamp() * 1000),
                    },
                }
            )
        return record

    async def ingest_batch(self, batch: EventBatch) -> List[EventRecord]:
        return [await self.ingest(event) for event in batch.events]

    def _dispatch(self, event: EventEnvelope, aligned_ts: datetime) -> Dict[str, object]:
        results: Dict[str, object] = {}
        if event.stream_type == StreamType.somatic and self.somatic_processor:
            results["somatic"] = self.somatic_processor.process(event, aligned_ts)
        if event.stream_type in {StreamType.text, StreamType.audio, StreamType.video} and self.symbolic_processor:
            sym_res = self.symbolic_processor.process(event)
            if sym_res is not None:
                results["symbolic"] = sym_res
        if self.noetic_processor and (
            event.payload.get("feature_matrix") is not None
            or event.payload.get("hrv_sdnn_mean") is not None
            or event.payload.get("hrv_rmssd_ms") is not None
            or event.payload.get("accuracy") is not None
        ):
            noetic_score = self.noetic_processor.process(event)
            if noetic_score is not None:
                results["noetic_coherence"] = noetic_score
        return results

    @staticmethod
    def to_batch_response(records: List[EventRecord]) -> BatchIngestResponse:
        return BatchIngestResponse(ingested=[EventReceipt.from_record(r) for r in records])

    @staticmethod
    def _summarize_results(results: Dict[str, object]) -> Dict[str, object]:
        metrics: Dict[str, object] = {}
        somatic_res = results.get("somatic")
        if isinstance(somatic_res, dict):
            windows = somatic_res.get("windows") or []
            means = [w.get("mean") for w in windows if isinstance(w, dict) and w.get("mean") is not None]
            if means:
                metrics["somatic_arousal"] = float(sum(means) / len(means))
        if "noetic_coherence" in results:
            try:
                metrics["noetic_coherence"] = float(results["noetic_coherence"])
            except (TypeError, ValueError):
                pass
        symbolic_res = results.get("symbolic")
        if isinstance(symbolic_res, dict):
            action = symbolic_res.get("action")
            if action:
                metrics["symbolic_action"] = action
        return metrics

    @staticmethod
    def _message_type(event: EventEnvelope) -> str:
        if event.stream_type == StreamType.somatic:
            return "somatic_state"
        if event.stream_type in {StreamType.text, StreamType.audio, StreamType.video}:
            return "symbolic_state"
        return "noetic_state"
