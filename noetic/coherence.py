from __future__ import annotations

from typing import Dict, List

import numpy as np


def coherence_score(feature_matrix: np.ndarray, weights: Dict[str, float] | None = None) -> float:
    if feature_matrix.size == 0:
        return 0.0
    corr = np.corrcoef(feature_matrix)
    if np.isnan(corr).all():
        return 0.0
    upper = corr[np.triu_indices_from(corr, k=1)]
    base_score = float(np.nanmean(np.abs(upper))) if upper.size else 0.0
    if weights:
        weight_penalty = sum(weights.values()) / max(len(weights), 1)
        return float(base_score - 0.1 * weight_penalty)
    return base_score


class NoeticAnalyzer:
    def __init__(self, weight_coherence: float = 0.5, weight_entropy: float = 0.3, weight_stability: float = 0.2):
        self.weight_coherence = weight_coherence
        self.weight_entropy = weight_entropy
        self.weight_stability = weight_stability

    def compute_coherence(self, feature_matrix: np.ndarray, entropy: float, stability: float) -> float:
        corr_score = coherence_score(feature_matrix)
        return float(
            self.weight_coherence * corr_score
            - self.weight_entropy * entropy
            + self.weight_stability * stability
        )

    def coherence_stream(self, matrices: List[np.ndarray], entropies: List[float], stabilities: List[float]) -> List[float]:
        scores: List[float] = []
        for matrix, ent, stab in zip(matrices, entropies, stabilities):
            scores.append(self.compute_coherence(matrix, ent, stab))
        return scores
