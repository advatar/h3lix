from __future__ import annotations

from enum import Enum
from typing import Dict, Iterable, List, Set

from streams.models import StreamType


class Scope(str, Enum):
    wearables = "wearables"
    text = "text"
    audio = "audio"
    video = "video"
    task = "task"
    meta = "meta"


STREAM_SCOPE_MAP = {
    StreamType.somatic: Scope.wearables.value,
    StreamType.text: Scope.text.value,
    StreamType.audio: Scope.audio.value,
    StreamType.video: Scope.video.value,
    StreamType.task: Scope.task.value,
    StreamType.meta: Scope.meta.value,
}


class ConsentManager:
    """Tracks per-participant scopes and enforces basic consent."""

    def __init__(self, default_allow: bool = False):
        self.default_allow = default_allow
        self._scopes: Dict[str, Set[str]] = {}

    def set_scopes(self, participant_id: str, scopes: Iterable[str]) -> None:
        self._scopes[participant_id] = {s for s in scopes}

    def get_scopes(self, participant_id: str) -> List[str]:
        return sorted(self._scopes.get(participant_id, []))

    def ensure_allowed(self, participant_id: str, scope: str) -> None:
        allowed = self._scopes.get(participant_id)
        if allowed is None:
            if self.default_allow:
                return
            raise PermissionError(f"No consent recorded for participant {participant_id} (scope={scope})")
        if scope not in allowed:
            raise PermissionError(f"Scope '{scope}' not allowed for participant {participant_id}")
