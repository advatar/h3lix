from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np


@dataclass
class RogueVariable:
    feature: str
    score: float
    threshold: float
    zscore: float


class RogueVariableDetector:
    def __init__(self, sigma: float = 3.0):
        self.sigma = sigma

    def detect(self, shap_values: Sequence[float], feature_names: Sequence[str]) -> List[RogueVariable]:
        values = np.abs(np.asarray(shap_values, dtype=float))
        if values.size == 0:
            return []
        # Use a trimmed estimate (exclude the current max) to avoid the outlier inflating the threshold.
        if values.size >= 2:
            max_idx = int(np.argmax(values))
            trimmed = np.delete(values, max_idx)
            mean = float(trimmed.mean())
            std = float(trimmed.std())
        else:
            mean = float(values.mean())
            std = float(values.std())
        threshold = mean + self.sigma * std
        rvs: List[RogueVariable] = []
        for value, name in zip(values, feature_names):
            if value >= threshold:
                z = (value - mean) / (std + 1e-9)
                rvs.append(RogueVariable(feature=name, score=float(value), threshold=threshold, zscore=float(z)))
        return rvs

    def potency_index(self, factors: Dict[str, float]) -> float:
        weights = {
            "rate_of_change": 0.25,
            "breadth": 0.15,
            "amplification": 0.2,
            "affective_load": 0.15,
            "gate_leverage": 0.15,
            "robustness": 0.1,
        }
        score = 0.0
        for key, weight in weights.items():
            score += weight * factors.get(key, 0.0)
        return float(score)
