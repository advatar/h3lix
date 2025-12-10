from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.human_api import db as human_db
from mpg.clinical import fetch_plans
from mpg.repository import Neo4jMPGRepository, InMemoryMPGRepository


class MobileTrialConfig(BaseModel):
    trialId: str
    stimulusType: str
    stimulusPayload: str
    awarenessCondition: str
    maskType: Optional[str] = None
    decisionOptions: List[str]
    itiMs: int = 1000
    planId: Optional[str] = None


class MobileSessionRequest(BaseModel):
    participant_id: str
    notes: Optional[str] = None
    protocol_version: Optional[str] = "H3LIX_LAIZA_mobile"


class MobileSessionResponse(BaseModel):
    session_id: str
    participant_id: str


class MobileTrialResult(BaseModel):
    session_id: str
    stimulus_id: str
    awareness_condition: str
    mask_type: str
    trial_index: int
    decision: str
    rt_ms: float
    correct: Optional[bool] = None
    confidence: Optional[float] = None
    intuition_rating: Optional[float] = None
    awareness_question: Optional[str] = None
    awareness_response: Optional[str] = None
    awareness_accuracy: Optional[float] = None
    segments: List[str] = Field(default_factory=list)
    features: dict = Field(default_factory=dict)
    plan_id: Optional[str] = None
    clinical_session_id: Optional[str] = None
    notes: Optional[str] = None


def _load_trial_configs() -> List[MobileTrialConfig]:
    config_path = os.getenv("MOBILE_TRIAL_CONFIG", "configs/mobile_trials.json")
    path = Path(config_path)
    if not path.exists():
        # Fallback demo block
        return [
            MobileTrialConfig(
                trialId="demo-1",
                stimulusType="image",
                stimulusPayload="https://example.com/demo.png",
                awarenessCondition="FULL",
                maskType="NONE",
                decisionOptions=["A", "B"],
                itiMs=1200,
            ),
            MobileTrialConfig(
                trialId="demo-2",
                stimulusType="text",
                stimulusPayload="Choose the safer option",
                awarenessCondition="IU",
                maskType="BRIEF_MASK",
                decisionOptions=["SAFE", "RISKY"],
                itiMs=1500,
            ),
        ]
    try:
        data = json.loads(path.read_text())
        return [MobileTrialConfig(**item) for item in data]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to load mobile trial configs: {exc}") from exc


router = APIRouter(prefix="/mobile", tags=["mobile"])
repo_hint: Neo4jMPGRepository | InMemoryMPGRepository | None = None


@router.get("/experiments/{experiment_id}", response_model=List[MobileTrialConfig])
def get_experiment(experiment_id: str) -> List[MobileTrialConfig]:
    # experiment_id reserved for future selection; returns default block for now
    return _load_trial_configs()


@router.post("/session", response_model=MobileSessionResponse)
def create_mobile_session(body: MobileSessionRequest) -> MobileSessionResponse:
    sid = human_db.create_session(
        participant_id=body.participant_id,
        notes=body.notes,
        protocol_version=body.protocol_version or "H3LIX_LAIZA_mobile",
    )
    return MobileSessionResponse(session_id=sid, participant_id=body.participant_id)


@router.post("/trial_result")
def submit_trial_result(body: MobileTrialResult) -> dict:
    tid = human_db.create_trial(
        session_id=body.session_id,
        stimulus_id=body.stimulus_id,
        awareness_condition=body.awareness_condition,
        mask_type=body.mask_type,
        trial_index=body.trial_index,
        features={**body.features, "plan_id": body.plan_id, "clinical_session_id": body.clinical_session_id},
        segments=body.segments,
    )
    human_db.update_trial_human(
        trial_id=tid,
        choice=body.decision,
        rt_ms=body.rt_ms,
        correct=body.correct,
        confidence=body.confidence,
        intuition_rating=body.intuition_rating,
        notes=body.notes,
    )
    if body.awareness_question and body.awareness_response:
        human_db.create_awareness_check(
            tid,
            question=body.awareness_question,
            response=body.awareness_response,
            accuracy=body.awareness_accuracy,
        )
    if body.intuition_rating is not None or body.confidence is not None:
        human_db.create_self_report(
            tid,
            intuition_rating=body.intuition_rating,
            confidence_rating=body.confidence,
            felt_state=None,
            comment=body.notes,
        )
    return {"status": "ok", "trial_id": tid}


@router.get("/therapy_tasks/{participant_id}", response_model=List[MobileTrialConfig])
def therapy_tasks(participant_id: str, plan_id: Optional[str] = None) -> List[MobileTrialConfig]:
    # if repository is available, return plan homework tasks as trial configs
    if repo_hint is None:
        return _load_trial_configs()
    plans = fetch_plans(repo_hint, participant_id)
    if plan_id:
        plans = [p for p in plans if p.get("id") == plan_id]
    tasks: List[MobileTrialConfig] = []
    for plan in plans:
        hw = plan.get("homework_tasks") or []
        for idx, task in enumerate(hw):
            tasks.append(
                MobileTrialConfig(
                    trialId=f"{plan.get('id')}-task-{idx}",
                    stimulusType="text",
                    stimulusPayload=str(task),
                    awarenessCondition="FULL",
                    maskType=None,
                    decisionOptions=["continue"],
                    itiMs=1000,
                    planId=plan.get("id"),
                )
            )
    return tasks


@router.get("/protocol/{instance_id}/plan", response_model=List[MobileTrialConfig])
def protocol_plan(instance_id: str, participant_id: Optional[str] = None) -> List[MobileTrialConfig]:
    # re-use therapy_tasks for now; filter by plan if possible
    if repo_hint is None:
        return []
    plan_id = None
    if isinstance(repo_hint, Neo4jMPGRepository):
        rec = repo_hint.driver.session(database=repo_hint.database).run(
            """
            MATCH (pi:ProtocolInstance {id: $id})
            RETURN pi.plan_id AS pid, pi.participant_id AS participant_id
            """,
            id=instance_id,
        ).single()
        if rec:
            plan_id = rec.get("pid")
            participant_id = participant_id or rec.get("participant_id")
    return therapy_tasks(participant_id or "", plan_id=plan_id)
    return []
