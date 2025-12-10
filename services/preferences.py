from __future__ import annotations

from typing import Dict, List, Optional


class PreferenceStore:
    """In-memory preferences for interventions and segment visibility."""

    def __init__(self):
        self._intervention_prefs: Dict[str, List[str]] = {}
        self._segment_visibility: Dict[str, Dict[str, bool]] = {}

    def set_interventions(self, participant_id: str, types: List[str]) -> None:
        self._intervention_prefs[participant_id] = types

    def get_interventions(self, participant_id: str) -> List[str]:
        return self._intervention_prefs.get(participant_id, [])

    def set_segment_visibility(self, participant_id: str, segment_id: str, visible: bool) -> None:
        per_participant = self._segment_visibility.get(participant_id, {})
        per_participant[segment_id] = visible
        self._segment_visibility[participant_id] = per_participant

    def get_segment_visibility(self, participant_id: str, segment_id: str) -> Optional[bool]:
        return self._segment_visibility.get(participant_id, {}).get(segment_id)
