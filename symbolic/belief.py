from __future__ import annotations

import math
from typing import Dict, List

from core.models import BeliefState, Trial
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository


class SymbolicEngine:
    def __init__(self, repo: Neo4jMPGRepository | InMemoryMPGRepository):
        self.repo = repo

    def update_beliefs(self, stimulus: str, trial: Trial | None = None) -> BeliefState:
        weights = self._encode_stimulus(stimulus)
        total = sum(weights.values()) or 1.0
        distribution = {k: v / total for k, v in weights.items()}
        uncertainty = float(-sum(p * math.log(p + 1e-9) for p in distribution.values()))
        return BeliefState(
            trial_id=trial.id if trial else "unknown",
            hypotheses=distribution,
            uncertainty=uncertainty,
            supporting_nodes=[],
        )

    def choose_action(self, belief: BeliefState) -> str:
        if not belief.hypotheses:
            return "noop"
        return max(belief.hypotheses, key=belief.hypotheses.get)

    def update_with_feedback(self, belief: BeliefState, outcome: float) -> BeliefState:
        adjusted = {
            hypo: max(prob + outcome * 0.05, 0.0) for hypo, prob in belief.hypotheses.items()
        }
        total = sum(adjusted.values()) or 1.0
        normalized = {k: v / total for k, v in adjusted.items()}
        return belief.model_copy(update={"hypotheses": normalized})

    def _encode_stimulus(self, stimulus: str) -> Dict[str, float]:
        tokens = stimulus.lower().split()
        weights: Dict[str, float] = {"H0": 0.5, "H1": 0.5}
        if "risk" in tokens:
            weights["H1"] += 0.3
        if "safe" in tokens:
            weights["H0"] += 0.3
        if "reward" in tokens:
            weights["H1"] += 0.2
        return weights
