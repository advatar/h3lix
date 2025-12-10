from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional
import uuid

from mpg.models import EvidenceItem, MPGNode, SegmentState
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from streams.models import EventEnvelope, StreamType


class MPGSink:
    """Translates processed stream events into MPG evidence and SegmentState snapshots."""

    def __init__(self, repo: Neo4jMPGRepository | InMemoryMPGRepository):
        self.repo = repo

    def handle(self, event: EventEnvelope, results: Dict[str, Any], aligned_ts: datetime) -> None:
        if event.stream_type == StreamType.somatic and "somatic" in results:
            self._handle_somatic(event, results["somatic"], aligned_ts)
        if event.stream_type in {StreamType.text, StreamType.audio, StreamType.video} and "symbolic" in results:
            self._handle_symbolic(event, results["symbolic"], aligned_ts)
        if "noetic_coherence" in results:
            self._handle_noetic(event, float(results["noetic_coherence"]), aligned_ts)

    def _handle_somatic(self, event: EventEnvelope, somatic_res: Dict[str, Any], aligned_ts: datetime) -> None:
        segments = self._segments_for_event(event)
        arousal = self._estimate_arousal(somatic_res.get("windows", []))
        innovation = self._estimate_innovation(somatic_res.get("states", []))
        if segments:
            for seg in segments:
                self._ensure_segment(seg)
                state = SegmentState(
                    id=str(uuid.uuid4()),
                    segment_id=seg,
                    t=aligned_ts.timestamp(),
                    somatic_arousal=arousal,
                    innovation=innovation,
                    meta={"source": event.source},
                )
                self.repo.create_segment_state(seg, state)
                ev = self._evidence_from_event(
                    event,
                    aligned_ts,
                    description="Somatic summary",
                    snippet=f"arousal={arousal:.4f}, innovation={innovation:.4f}" if arousal is not None else "",
                    source_type="SOMATIC",
                )
                self.repo.create_evidence(ev, target_node_id=seg)

    def _handle_symbolic(self, event: EventEnvelope, sym_res: Dict[str, Any], aligned_ts: datetime) -> None:
        text = event.payload.get("text") or event.payload.get("transcript") or ""
        snippet = (
            text
            or event.payload.get("snippet")
            or event.payload.get("subject")
            or ""
        )[:240]
        segments = self._segments_for_event(event)
        ev = self._evidence_from_event(
            event,
            aligned_ts,
            description="Symbolic update",
            snippet=snippet,
            source_type="SYMBOLIC",
        )
        if segments:
            for seg in segments:
                self._ensure_segment(seg)
                self.repo.create_evidence(ev, target_node_id=seg)
        else:
            self.repo.create_evidence(ev, target_node_id=None)

    def _handle_noetic(self, event: EventEnvelope, coherence: float, aligned_ts: datetime) -> None:
        segments = self._segments_for_event(event)
        if not segments:
            return
        for seg in segments:
            self._ensure_segment(seg)
            state = SegmentState(
                id=str(uuid.uuid4()),
                segment_id=seg,
                t=aligned_ts.timestamp(),
                coherence=coherence,
                meta={"source": event.source},
            )
            self.repo.create_segment_state(seg, state)
            ev = self._evidence_from_event(
                event,
                aligned_ts,
                description="Noetic coherence",
                snippet=f"coherence={coherence:.4f}",
                source_type="NOETIC",
            )
            self.repo.create_evidence(ev, target_node_id=seg)

    def _segments_for_event(self, event: EventEnvelope) -> List[str]:
        if event.segments:
            return [str(s) for s in event.segments]
        segments = event.payload.get("segments") or event.payload.get("segment_ids") or event.payload.get("segment")
        if isinstance(segments, str):
            return [segments]
        if isinstance(segments, list):
            return [str(s) for s in segments]
        return []

    def _ensure_segment(self, segment_id: str) -> None:
        if self.repo.node_exists(segment_id):
            return
        placeholder = MPGNode(
            id=segment_id,
            name=f"Segment {segment_id}",
            layers=[],
            valence=0.0,
            intensity=0.0,
            recency=0.0,
            stability=0.0,
            importance=0.0,
            confidence=0.0,
            reasoning="Placeholder segment created from stream event",
            level=1,
        )
        self.repo.create_node(placeholder, label="Segment")

    @staticmethod
    def _estimate_arousal(windows: List[Dict[str, Any]]) -> Optional[float]:
        if not windows:
            return None
        means = [w.get("mean") for w in windows if w.get("mean") is not None]
        if not means:
            return None
        return float(mean(means))

    @staticmethod
    def _estimate_innovation(states: List[Any]) -> Optional[float]:
        if not states:
            return None
        innovations: List[float] = []
        for state in states:
            innov = getattr(state, "innovation", None)
            if innov is None and isinstance(state, dict):
                innov = state.get("innovation")
            if innov is not None:
                try:
                    innovations.append(float(innov))
                except (TypeError, ValueError):
                    continue
        if not innovations:
            return None
        return float(mean(innovations))

    @staticmethod
    def _evidence_from_event(
        event: EventEnvelope,
        aligned_ts: datetime,
        description: str,
        snippet: str,
        source_type: str,
    ) -> EvidenceItem:
        quality = event.quality.signal_to_noise if event.quality and event.quality.signal_to_noise is not None else 1.0
        return EvidenceItem(
            id=str(uuid.uuid4()),
            description=description,
            source_type=source_type,
            pointer=event.event_id,
            snippet=snippet,
            timestamp=aligned_ts.timestamp(),
            c=1.0,
            q=float(quality),
            u=1.0,
            t=1.0,
        )
