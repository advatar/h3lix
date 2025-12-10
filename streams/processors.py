from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from core.models import SomaticSample, Trial
from noetic.coherence import NoeticAnalyzer
from somatic.processor import SomaticFeatureExtractor
from symbolic.belief import SymbolicEngine
from streams.models import EventEnvelope


class SomaticEventProcessor:
    """Normalizes somatic payloads into SomaticSamples and basic features."""

    def __init__(self, extractor: SomaticFeatureExtractor):
        self.extractor = extractor

    @staticmethod
    def _parse_sample_timestamp(sample: Dict[str, Any], aligned_event_ts: datetime) -> float:
        if "timestamp_utc" in sample:
            ts = sample["timestamp_utc"]
            if isinstance(ts, (int, float)):
                return float(ts)
            if isinstance(ts, str):
                try:
                    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    pass
            if isinstance(ts, datetime):
                return ts.timestamp()
        if "offset_ms" in sample:
            return (aligned_event_ts + timedelta(milliseconds=float(sample["offset_ms"]))).timestamp()
        return aligned_event_ts.timestamp()

    def _to_samples(self, event: EventEnvelope, aligned_ts: datetime) -> List[SomaticSample]:
        payload_samples = event.payload.get("samples") or []
        samples: List[SomaticSample] = []
        trial_id = event.payload.get("trial_id", "")
        for raw in payload_samples:
            if "value" not in raw:
                continue
            channel = str(raw.get("channel") or raw.get("sensor") or "unknown")
            try:
                value = float(raw["value"])
            except (TypeError, ValueError):
                continue
            timestamp = self._parse_sample_timestamp(raw, aligned_ts)
            samples.append(
                SomaticSample(
                    user_id=event.participant_id,
                    trial_id=trial_id,
                    timestamp=timestamp,
                    channel=channel,
                    value=value,
                )
            )
        return samples

    def process(self, event: EventEnvelope, aligned_ts: datetime) -> Dict[str, Any]:
        samples = self._to_samples(event, aligned_ts)
        if not samples:
            return {"samples": [], "windows": [], "states": []}
        windows = self.extractor.window_features(samples)
        states = self.extractor.kalman_filter(samples)
        return {"samples": samples, "windows": windows, "states": states}


class SymbolicEventProcessor:
    """Parses text-like payloads into SymbolicEngine belief updates."""

    def __init__(self, engine: SymbolicEngine):
        self.engine = engine

    def process(self, event: EventEnvelope) -> Optional[Dict[str, Any]]:
        text = event.payload.get("text") or event.payload.get("transcript")
        if not text:
            return None
        trial = event.payload.get("trial")
        trial_obj: Optional[Trial] = None
        if isinstance(trial, dict):
            try:
                trial_obj = Trial(**trial)
            except Exception:
                trial_obj = None
        belief = self.engine.update_beliefs(text, trial=trial_obj)
        action = self.engine.choose_action(belief)
        return {"belief": belief, "action": action}


class NoeticEventProcessor:
    """Computes coherence metrics from aligned windows of features."""

    def __init__(self, analyzer: NoeticAnalyzer):
        self.analyzer = analyzer

    def process(self, event: EventEnvelope) -> Optional[float]:
        matrix = event.payload.get("feature_matrix")
        entropy = float(event.payload.get("entropy", 0.0))
        stability = float(event.payload.get("stability", 0.0))
        if matrix is not None:
            arr = np.asarray(matrix, dtype=float)
            return float(self.analyzer.compute_coherence(arr, entropy=entropy, stability=stability))

        # Lightweight fallback for Phase 1: blend HRV + task accuracy into a coherence-like score.
        hrv = (
            event.payload.get("hrv_rmssd_ms")
            if event.payload.get("hrv_rmssd_ms") is not None
            else event.payload.get("hrv_sdnn_mean")
        )
        accuracy = event.payload.get("accuracy")
        if hrv is None and accuracy is None:
            return None
        try:
            hrv_norm = max(0.0, min(float(hrv) / 120.0, 1.0)) if hrv is not None else 0.0  # cap SDNN at ~120ms
        except (TypeError, ValueError):
            hrv_norm = 0.0
        try:
            acc_norm = max(0.0, min(float(accuracy), 1.0)) if accuracy is not None else 0.0
        except (TypeError, ValueError):
            acc_norm = 0.0
        return float(0.6 * hrv_norm + 0.4 * acc_norm)
