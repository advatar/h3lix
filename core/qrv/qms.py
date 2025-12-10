from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from core.qrv.models import QMSState


class QMSBuilder:
    def __init__(
        self,
        repo: Neo4jMPGRepository | InMemoryMPGRepository,
        weights: Dict[str, float] | None = None,
        include_state_metrics: bool = True,
    ):
        self.repo = repo
        self.weights = weights or {
            "importance": 0.4,
            "confidence": 0.25,
            "stability": 0.1,
            "recency": 0.1,
            "intensity": 0.1,
            "valence": 0.05,
            "coherence": 0.15,
            "potency": 0.1,
        }
        self.include_state_metrics = include_state_metrics

    def _latest_state(self, segment_id: str) -> Tuple[float, float]:
        """Return (coherence, potency) from latest SegmentState if present."""
        if not self.include_state_metrics:
            return (0.0, 0.0)
        try:
            states = self.repo.get_segment_states(segment_id, limit=1)
        except Exception:
            return (0.0, 0.0)
        if not states:
            return (0.0, 0.0)
        st = states[0]
        return (float(st.get("coherence") or 0.0), float(st.get("potency") or 0.0))

    def _amplitude_from_segment(self, segment: Dict) -> float:
        total = 0.0
        coherence, potency = self._latest_state(segment.get("id"))
        for key, weight in self.weights.items():
            if key == "coherence":
                total += weight * coherence
            elif key == "potency":
                total += weight * potency
            else:
                total += weight * float(segment.get(key, 0.0))
        return total

    def build_from_segments(
        self,
        session_id: str,
        t_rel_ms: float,
        limit: int = 64,
        feature_overrides: Sequence[float] | None = None,
    ) -> QMSState:
        segments = self.repo.top_segments(limit=limit)
        basis = [seg["id"] for seg in segments]
        amplitudes = np.array([self._amplitude_from_segment(seg) for seg in segments], dtype=np.complex128)
        if feature_overrides is not None:
            overrides = np.array(feature_overrides, dtype=np.complex128)
            if overrides.size:
                overrides = overrides[: amplitudes.size]
                amplitudes[: overrides.size] += overrides
        norm = float(np.linalg.norm(amplitudes))
        if norm > 0:
            amplitudes = amplitudes / norm
        return QMSState(
            basis=basis,
            amplitudes=amplitudes.tolist(),
            session_id=session_id,
            t_rel_ms=t_rel_ms,
            norm=norm,
        )
