from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from experiments.human_runner import HumanNeo4j

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")

db = HumanNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
db.init_schema()

router = APIRouter(prefix="/human", tags=["human"])


class ParticipantCreate(BaseModel):
    alias: str
    age_band: Optional[str] = None
    gender: Optional[str] = None


@router.post("/participant")
def create_participant(p: ParticipantCreate) -> Dict[str, Any]:
    pid = db.create_participant(p.alias, p.age_band, p.gender)
    return {"participant_id": pid}


class SessionCreate(BaseModel):
    participant_id: str
    notes: Optional[str] = None
    protocol_version: Optional[str] = "H3LIX_LAIZA_v1"


@router.post("/session")
def create_session(s: SessionCreate) -> Dict[str, Any]:
    sid = db.create_session(s.participant_id, s.notes, protocol_version=s.protocol_version or "H3LIX_LAIZA_v1")
    return {"session_id": sid}


class TrialStart(BaseModel):
    session_id: str
    stimulus_id: str
    awareness_condition: str
    mask_type: str
    trial_index: int
    features: Dict[str, float] = {}
    segments: List[str] = []


@router.post("/trial")
def start_trial(t: TrialStart) -> Dict[str, Any]:
    tid = db.create_trial(
        session_id=t.session_id,
        stimulus_id=t.stimulus_id,
        awareness_condition=t.awareness_condition,
        mask_type=t.mask_type,
        trial_index=t.trial_index,
        features=t.features,
        segments=t.segments,
    )
    return {"trial_id": tid}


class TrialHumanUpdate(BaseModel):
    choice: Any
    rt_ms: float
    correct: Optional[bool] = None
    confidence: Optional[float] = None
    intuition_rating: Optional[float] = None
    notes: Optional[str] = None


@router.post("/trial/{trial_id}/human")
def update_trial_human(trial_id: str, body: TrialHumanUpdate) -> Dict[str, Any]:
    db.update_trial_human(
        trial_id=trial_id,
        choice=body.choice,
        rt_ms=body.rt_ms,
        correct=body.correct,
        confidence=body.confidence,
        intuition_rating=body.intuition_rating,
        notes=body.notes,
    )
    return {"status": "ok"}


class TrialSelfReport(BaseModel):
    intuition_rating: Optional[float] = None
    confidence_rating: Optional[float] = None
    felt_state: Optional[str] = None
    comment: Optional[str] = None


@router.post("/trial/{trial_id}/self_report")
def add_self_report(trial_id: str, body: TrialSelfReport) -> Dict[str, Any]:
    rid = db.create_self_report(
        trial_id,
        intuition_rating=body.intuition_rating,
        confidence_rating=body.confidence_rating,
        felt_state=body.felt_state,
        comment=body.comment,
    )
    return {"self_report_id": rid}


class TrialAwareness(BaseModel):
    question: str
    response: str
    accuracy: Optional[float] = None


@router.post("/trial/{trial_id}/awareness")
def add_awareness(trial_id: str, body: TrialAwareness) -> Dict[str, Any]:
    aid = db.create_awareness_check(trial_id, body.question, body.response, body.accuracy)
    return {"awareness_check_id": aid}


@router.get("/participant/{participant_id}/sessions")
def list_sessions(participant_id: str) -> List[Dict[str, Any]]:
    records = db.run(
        """
        MATCH (p:Participant {id: $pid})-[:HAS_SESSION]->(s:Session)
        RETURN s
        ORDER BY s.started_at DESC
        """,
        pid=participant_id,
    )
    return [dict(r["s"]) for r in records]


@router.get("/session/{session_id}/trials")
def list_trials(session_id: str) -> List[Dict[str, Any]]:
    records = db.run(
        """
        MATCH (:Session {id: $sid})-[:HAS_TRIAL]->(t:Trial)
        RETURN t
        ORDER BY t.index ASC
        """,
        sid=session_id,
    )
    return [dict(r["t"]) for r in records]


@router.get("/trial/{trial_id}")
def get_trial(trial_id: str) -> Dict[str, Any]:
    records = db.run(
        """
        MATCH (t:Trial {id: $tid})
        OPTIONAL MATCH (t)-[:HAS_MUFS]->(m:MUFS)
        RETURN t, collect(m) AS mufs
        """,
        tid=trial_id,
    )
    if not records:
        raise HTTPException(status_code=404, detail="Trial not found")
    rec = records[0]
    trial_data = dict(rec["t"])
    mufs = [dict(m) for m in rec["mufs"] if m]
    trial_data["mufs"] = mufs
    return trial_data
