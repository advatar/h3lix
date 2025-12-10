from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AdaptationSuggestion:
    protocol_instance_id: str
    suggested_action: str  # "advance" | "repeat" | "emphasize" | "deemphasize"
    target_module_id: str | None
    rationale: str


class ProtocolPersonalizationEngine:
    """Simple heuristic PPE placeholder; replace with full scoring/bandit logic."""

    def __init__(self, advance_threshold: float = 0.2, repeat_threshold: float = -0.1):
        self.advance_threshold = advance_threshold
        self.repeat_threshold = repeat_threshold

    def suggest(self, module_scores: Dict[str, float], current_module_id: str | None, protocol_instance_id: str) -> AdaptationSuggestion | None:
        if current_module_id is None:
            return None
        score = module_scores.get(current_module_id, 0.0)
        if score >= self.advance_threshold:
            return AdaptationSuggestion(
                protocol_instance_id=protocol_instance_id,
                suggested_action="advance",
                target_module_id=current_module_id,
                rationale=f"Module score {score:.3f} >= advance threshold {self.advance_threshold}",
            )
        if score <= self.repeat_threshold:
            return AdaptationSuggestion(
                protocol_instance_id=protocol_instance_id,
                suggested_action="repeat",
                target_module_id=current_module_id,
                rationale=f"Module score {score:.3f} <= repeat threshold {self.repeat_threshold}",
            )
        return AdaptationSuggestion(
            protocol_instance_id=protocol_instance_id,
            suggested_action="hold",
            target_module_id=current_module_id,
            rationale=f"Module score {score:.3f} within thresholds; hold pace",
        )
