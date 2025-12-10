from __future__ import annotations

from typing import Dict, List, Optional
import uuid
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.authz import ensure_role
from api.human_api import db as human_db
from mpg.clinical import (
    ClinicalSession,
    InterventionPlan,
    ClinicalEpisode,
    ClinicalNote,
    create_clinical_session,
    create_intervention_plan,
    create_episode,
    create_note,
    fetch_plans,
    fetch_notes,
    fetch_episodes,
)
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from streams.store import InMemoryEventStore, PostgresEventStore


class ClinicalSessionStart(BaseModel):
    participant_id: str
    clinician_id: str
    mode: str = "TELEHEALTH"
    session_number: int = 1
    goals: List[str] = Field(default_factory=list)


class ClinicalSessionEnd(BaseModel):
    session_id: str


class InterventionPlanCreate(BaseModel):
    participant_id: str
    name: str
    type: str
    targets: List[str] = Field(default_factory=list)
    homework_tasks: List[str] = Field(default_factory=list)
    intended_duration: Optional[str] = None
    success_criteria: Optional[str] = None
    risk_level: Optional[str] = None


class SnapshotResponse(BaseModel):
    participant_id: str
    segments: List[Dict]
    intuition_trials: List[Dict]
    recent_events: int
    coherence: Optional[float] = None


class ClinicalEpisodeCreate(BaseModel):
    session_id: str
    title: Optional[str] = None
    focus_segment: Optional[str] = None
    trial_id: Optional[str] = None


class ClinicalNoteCreate(BaseModel):
    session_id: str
    author: str
    text: str


class ClinicalPlanResponse(BaseModel):
    plans: List[Dict]


def build_clinical_router(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    event_store: InMemoryEventStore | PostgresEventStore,
) -> APIRouter:
    router = APIRouter(prefix="/clinical", tags=["clinical"])

    @router.post("/session/start")
    def start_session(request: Request, body: ClinicalSessionStart) -> dict:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        session = ClinicalSession(
            id=str(uuid.uuid4()),
            participant_id=body.participant_id,
            clinician_id=body.clinician_id,
            start_time=time.time(),
            end_time=None,
            mode=body.mode,
            session_number=body.session_number,
            goals=body.goals,
            status="ONGOING",
        )
        create_clinical_session(repo, session)
        return {"session_id": session.id, "status": "started"}

    @router.post("/session/end")
    def end_session(request: Request, body: ClinicalSessionEnd) -> dict:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        if isinstance(repo, Neo4jMPGRepository):
            repo.driver.session(database=repo.database).run(
                """
                MATCH (s:ClinicalSession {id: $id})
                SET s.end_time = datetime(), s.status = "COMPLETED"
                """,
                id=body.session_id,
            )
        return {"session_id": body.session_id, "status": "completed"}

    @router.post("/intervention_plan")
    def create_plan(request: Request, body: InterventionPlanCreate) -> dict:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        plan = InterventionPlan(
            id=str(uuid.uuid4()),
            name=body.name,
            type=body.type,
            targets=body.targets,
            homework_tasks=body.homework_tasks,
            intended_duration=body.intended_duration,
            success_criteria=body.success_criteria,
            risk_level=body.risk_level,
        )
        create_intervention_plan(repo, plan, participant_id=body.participant_id)
        return {"plan_id": plan.id, "status": "created"}

    @router.get("/session/{participant_id}/snapshot", response_model=SnapshotResponse)
    def session_snapshot(request: Request, participant_id: str) -> SnapshotResponse:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        segments = repo.top_segments(limit=5)
        recent = len(event_store.list(participant_id, limit=50))
        intuition = human_db.run(
            """
            MATCH (p:Participant {id: $pid})-[:HAS_SESSION]->(:Session)-[:HAS_TRIAL]->(t:Trial)
            WHERE coalesce(t.mpg_intuitive, false) = true
            RETURN t
            ORDER BY t.created_at DESC
            LIMIT 10
            """,
            pid=participant_id,
        )
        trials = [dict(r["t"]) for r in intuition]
        coherence_vals: List[float] = []
        for seg in segments:
            states = repo.get_segment_states(seg["id"], limit=5)
            for st in states:
                if st.get("coherence") is not None:
                    try:
                        coherence_vals.append(float(st["coherence"]))
                    except (TypeError, ValueError):
                        continue
        coherence = float(sum(coherence_vals) / len(coherence_vals)) if coherence_vals else None
        return SnapshotResponse(
            participant_id=participant_id,
            segments=segments,
            intuition_trials=trials,
            recent_events=recent,
            coherence=coherence,
        )

    @router.post("/episode")
    def create_clinical_episode(request: Request, body: ClinicalEpisodeCreate) -> dict:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        ep = ClinicalEpisode(
            id=str(uuid.uuid4()),
            session_id=body.session_id,
            focus_segment=body.focus_segment,
            trial_id=body.trial_id,
            title=body.title,
        )
        create_episode(repo, ep)
        return {"episode_id": ep.id, "status": "created"}

    @router.post("/note")
    def add_note(request: Request, body: ClinicalNoteCreate) -> dict:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        note = ClinicalNote(
            id=str(uuid.uuid4()),
            session_id=body.session_id,
            author=body.author,
            text=body.text,
        )
        create_note(repo, note)
        return {"note_id": note.id, "status": "created"}

    @router.get("/plans/{participant_id}", response_model=ClinicalPlanResponse)
    def list_plans(request: Request, participant_id: str) -> ClinicalPlanResponse:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        plans = fetch_plans(repo, participant_id)
        return ClinicalPlanResponse(plans=plans)

    @router.get("/session/{session_id}/notes")
    def list_notes(request: Request, session_id: str) -> List[Dict]:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        return fetch_notes(repo, session_id)

    @router.get("/session/{session_id}/episodes")
    def list_episodes(request: Request, session_id: str) -> List[Dict]:
        ensure_role(request, allowed={"clinician", "admin", "researcher"})
        return fetch_episodes(repo, session_id)

    return router
