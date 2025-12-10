from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from core.qrv.models import HILDPrompt, HILDState, HILDStatus, RogueDetectionResult


@dataclass
class HILDSessionState:
    status: HILDStatus
    unanswered_retry: bool = False


class HILDStateMachine:
    def __init__(self):
        self.sessions: Dict[str, HILDSessionState] = {}

    def get_status(self, session_id: str) -> HILDStatus:
        state = self.sessions.get(session_id)
        if not state:
            return HILDStatus(session_id=session_id, state=HILDState.idle)
        return state.status

    def _make_prompt(self, detection: RogueDetectionResult) -> HILDPrompt:
        anchor = "We observed a divergence between expected and current state."
        ambiguity = f"Segments {', '.join(detection.rogue_segments[:3])} carry unusual loadings."
        request = "Which activity or context best describes your current state?"
        return HILDPrompt(anchor=anchor, ambiguity=ambiguity, request=request)

    def on_tick(self, session_id: str, t_rel_ms: float, detection: RogueDetectionResult) -> HILDStatus:
        state = self.sessions.get(session_id)
        if not state:
            state = HILDSessionState(
                status=HILDStatus(session_id=session_id, state=HILDState.idle, last_transition_ms=t_rel_ms)
            )
            self.sessions[session_id] = state

        status = state.status

        if detection.triggered and status.state in {HILDState.idle, HILDState.resolved}:
            prompt = self._make_prompt(detection)
            status = HILDStatus(
                session_id=session_id,
                state=HILDState.clarifying,
                active_event_id=detection.event_id,
                prompt=prompt,
                last_transition_ms=t_rel_ms,
            )
            state.status = status
            state.unanswered_retry = False
            return status

        if detection.triggered and status.state == HILDState.clarifying:
            # already clarifying; keep prompt alive
            return status

        if not detection.triggered and status.state == HILDState.clarifying:
            # no new evidence but still unresolved; if we already retried, go passive-safe
            if state.unanswered_retry:
                status = HILDStatus(
                    session_id=session_id,
                    state=HILDState.passive_safe,
                    active_event_id=status.active_event_id,
                    prompt=status.prompt,
                    last_transition_ms=t_rel_ms,
                )
                state.status = status
            else:
                state.unanswered_retry = True
            return state.status

        if status.state == HILDState.passive_safe and not detection.triggered:
            status = HILDStatus(
                session_id=session_id,
                state=HILDState.resolved,
                active_event_id=status.active_event_id,
                last_transition_ms=t_rel_ms,
            )
            state.status = status
            return status

        return status

    def acknowledge(self, session_id: str, response: str, t_rel_ms: float) -> HILDStatus:
        state = self.sessions.get(session_id)
        if not state:
            status = HILDStatus(session_id=session_id, state=HILDState.idle, last_transition_ms=t_rel_ms)
            self.sessions[session_id] = HILDSessionState(status=status)
            return status
        status = HILDStatus(
            session_id=session_id,
            state=HILDState.resolved,
            active_event_id=state.status.active_event_id,
            last_transition_ms=t_rel_ms,
            prompt=None,
        )
        self.sessions[session_id] = HILDSessionState(status=status)
        return status
