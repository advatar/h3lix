from __future__ import annotations

from statistics import mean
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.human_api import db as human_db
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from services.preferences import PreferenceStore
from streams import ConsentManager
from streams.store import InMemoryEventStore, PostgresEventStore


class SegmentSummary(BaseModel):
    id: str
    name: str
    valence: float
    intensity: float
    importance: float
    confidence: float
    potency: Optional[float] = None
    rv: Optional[bool] = None
    visible: bool = True
    evidence_hint: Optional[str] = None


class ParticipantSummary(BaseModel):
    participant_id: str
    coherence: Optional[float] = None
    recent_events: int = 0
    top_segments: List[SegmentSummary] = Field(default_factory=list)
    intuition_trials: List[Dict] = Field(default_factory=list)


class SegmentFeedback(BaseModel):
    segment_id: str
    action: str  # "rename" | "hide" | "show" | "confirm"
    new_name: Optional[str] = None
    importance: Optional[float] = None


class InterventionPrefs(BaseModel):
    allowed_types: List[str] = Field(default_factory=list)


class ScopeUpdate(BaseModel):
    scopes: List[str]


def _coherence_from_states(repo: Neo4jMPGRepository | InMemoryMPGRepository, seg_id: str) -> Optional[float]:
    states = repo.get_segment_states(seg_id, limit=5)
    vals = [s.get("coherence") for s in states if s.get("coherence") is not None]
    return float(mean(vals)) if vals else None


def _top_segments(repo: Neo4jMPGRepository | InMemoryMPGRepository, limit: int = 5) -> List[SegmentSummary]:
    segs = repo.top_segments(limit=limit)
    summaries: List[SegmentSummary] = []
    for seg in segs:
        summaries.append(
            SegmentSummary(
                id=seg["id"],
                name=seg.get("name", ""),
                valence=float(seg.get("valence", 0.0)),
                intensity=float(seg.get("intensity", 0.0)),
                importance=float(seg.get("importance", 0.0)),
                confidence=float(seg.get("confidence", 0.0)),
                potency=seg.get("potency"),
                rv=seg.get("rv"),
                visible=seg.get("visible", True),
                evidence_hint=seg.get("reasoning"),
            )
        )
    return summaries


def _intuition_trials(participant_id: str) -> List[Dict]:
    records = human_db.run(
        """
        MATCH (p:Participant {id: $pid})-[:HAS_SESSION]->(:Session)-[:HAS_TRIAL]->(t:Trial)
        WHERE coalesce(t.mpg_intuitive, false) = true
        RETURN t
        ORDER BY t.created_at DESC
        LIMIT 20
        """,
        pid=participant_id,
    )
    return [dict(r["t"]) for r in records]


def build_participant_router(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    consent_manager: ConsentManager,
    preferences: PreferenceStore,
    event_store: InMemoryEventStore | PostgresEventStore,
) -> APIRouter:
    router = APIRouter(prefix="/participant", tags=["participant"])

    @router.get("/{participant_id}/summary", response_model=ParticipantSummary)
    def participant_summary(participant_id: str) -> ParticipantSummary:
        segments = _top_segments(repo, limit=5)
        coherence_vals = [c for s in segments if (c := _coherence_from_states(repo, s.id)) is not None]
        recent = len(event_store.list(participant_id, limit=50))
        intuition = _intuition_trials(participant_id)
        return ParticipantSummary(
            participant_id=participant_id,
            coherence=float(mean(coherence_vals)) if coherence_vals else None,
            recent_events=recent,
            top_segments=segments,
            intuition_trials=intuition,
        )

    @router.get("/{participant_id}/segments/top", response_model=List[SegmentSummary])
    def top_segments(participant_id: str, limit: int = 5) -> List[SegmentSummary]:
        return _top_segments(repo, limit=limit)

    @router.post("/{participant_id}/segment_feedback")
    def segment_feedback(participant_id: str, body: SegmentFeedback) -> dict:
        if body.action == "rename" and body.new_name:
            repo.update_segment_metadata(body.segment_id, name=body.new_name)
        if body.importance is not None:
            repo.update_segment_metadata(body.segment_id, importance=body.importance)
        if body.action == "hide":
            repo.update_segment_metadata(body.segment_id, visible=False)
            preferences.set_segment_visibility(participant_id, body.segment_id, False)
        if body.action == "show":
            repo.update_segment_metadata(body.segment_id, visible=True)
            preferences.set_segment_visibility(participant_id, body.segment_id, True)
        return {"status": "ok", "segment_id": body.segment_id}

    @router.get("/{participant_id}/scopes")
    def get_scopes(participant_id: str) -> dict:
        return {"participant_id": participant_id, "scopes": consent_manager.get_scopes(participant_id)}

    @router.post("/{participant_id}/scopes")
    def set_scopes(participant_id: str, update: ScopeUpdate) -> dict:
        consent_manager.set_scopes(participant_id, update.scopes)
        return {"status": "ok", "participant_id": participant_id, "scopes": update.scopes}

    @router.get("/{participant_id}/intervention_prefs", response_model=InterventionPrefs)
    def get_prefs(participant_id: str) -> InterventionPrefs:
        return InterventionPrefs(allowed_types=preferences.get_interventions(participant_id))

    @router.post("/{participant_id}/intervention_prefs")
    def set_prefs(participant_id: str, prefs: InterventionPrefs) -> dict:
        preferences.set_interventions(participant_id, prefs.allowed_types)
        return {"status": "ok", "participant_id": participant_id, "allowed_types": prefs.allowed_types}

    return router
