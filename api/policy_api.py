from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from policies.contextual_bandit import ActionDef
from policies.policy_engine import PolicyEngine

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")

# Demo actions (whitelisted, low/medium risk)
demo_actions = [
    ActionDef(id="SLOW_DECISION", name="Slow Decision", params_template={"extra_ms": 300}),
    ActionDef(id="REQUEST_JUSTIFICATION", name="Request Justification", params_template={"length": "short"}),
    ActionDef(id="SURFACE_EVIDENCE", name="Surface Evidence", params_template={"max_items": 2}),
    ActionDef(id="FOCUS_SEGMENT", name="Focus Segment", params_template={"segment_id": None}),
    ActionDef(id="DEFOCUS_SEGMENT", name="Defocus Segment", params_template={"segment_id": None}),
    ActionDef(id="TAKE_BREAK", name="Take Break", params_template={"duration_ms": 60000}),
    ActionDef(id="SOFT_ALERT", name="Soft Alert", params_template={"message": "Check bias"}),
]

# Assume a small fixed context dimension for demo
CONTEXT_DIM = 8
policy_engine = PolicyEngine(actions=demo_actions, context_dim=CONTEXT_DIM, alpha=1.0, policy_id="policy-demo")

router = APIRouter(prefix="/policy", tags=["policy"])


class PolicyContext(BaseModel):
    trial_id: str
    context: List[float]
    rv_segment_ids: List[str] = []
    collective_segment_ids: List[str] = []


@router.post("/recommend")
def recommend_intervention(ctx: PolicyContext) -> Dict[str, Any]:
    if len(ctx.context) != CONTEXT_DIM:
        raise HTTPException(status_code=400, detail=f"context length must be {CONTEXT_DIM}")
    x = np.array(ctx.context, dtype=float)
    action, episode_id = policy_engine.recommend(
        trial_id=ctx.trial_id,
        x=x,
        rv_segment_ids=ctx.rv_segment_ids,
        collective_segment_ids=ctx.collective_segment_ids,
    )
    return {
        "episode_id": episode_id,
        "action_id": action.id,
        "action_name": action.name,
        "parameters": action.params_template,
    }


class PolicyFeedback(BaseModel):
    episode_id: str
    action_id: str
    context: List[float]
    reward: float
    delta_coherence: Optional[float] = None
    delta_accuracy: Optional[float] = None
    delta_rt: Optional[float] = None
    notes: Optional[str] = None
    human_override: bool = False
    override_type: Optional[str] = None


@router.post("/feedback")
def policy_feedback(fb: PolicyFeedback) -> Dict[str, Any]:
    if len(fb.context) != CONTEXT_DIM:
        raise HTTPException(status_code=400, detail=f"context length must be {CONTEXT_DIM}")
    x = np.array(fb.context, dtype=float)
    policy_engine.update(
        x=x,
        episode_id=fb.episode_id,
        action_id=fb.action_id,
        reward=float(fb.reward),
        delta_coherence=fb.delta_coherence,
        delta_accuracy=fb.delta_accuracy,
        delta_rt=fb.delta_rt,
        notes=fb.notes or "",
        human_override=fb.human_override,
        override_type=fb.override_type,
    )
    return {"status": "ok"}
