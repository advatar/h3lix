from __future__ import annotations

from typing import Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.authz import ensure_role
from mpg.protocols import instantiate_protocol
from mpg.protocol_state import (
    create_protocol_instance,
    list_instances,
    update_module_state_scores,
    update_step_state_scores,
)
from mpg.repository import Neo4jMPGRepository
from services.aggregation import ProtocolScoreAggregator
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository


class ProtocolInstanceRequest(BaseModel):
    participant_id: str


class ScoreUpdateRequest(BaseModel):
    module_scores: Dict[str, Dict[str, float]] = {}
    step_scores: Dict[str, Dict[str, float]] = {}


def build_protocols_router(repo: Neo4jMPGRepository | InMemoryMPGRepository) -> APIRouter:
    router = APIRouter(prefix="/clinical/protocols", tags=["protocols"])
    aggregator = ProtocolScoreAggregator(repo)

    @router.get("")
    def list_protocols(request: Request) -> List[Dict]:
        ensure_role(request, allowed={"clinician", "researcher", "admin"})
        if isinstance(repo, Neo4jMPGRepository):
            recs = repo.driver.session(database=repo.database).run(
                """
                MATCH (p:ClinicalProtocol)
                RETURN p
                ORDER BY p.name ASC
                """
            )
            return [dict(r["p"]) for r in recs]
        return [
            {"id": n.id, "name": getattr(n, "name", ""), "target_condition": getattr(n, "target_condition", "")}
            for n in repo.nodes.values()
            if n.__class__.__name__ == "ProtocolTemplate"
        ]

    @router.get("/{protocol_id}")
    def get_protocol(request: Request, protocol_id: str) -> Dict:
        ensure_role(request, allowed={"clinician", "researcher", "admin"})
        if isinstance(repo, Neo4jMPGRepository):
            session = repo.driver.session(database=repo.database)
            rec = session.run(
                """
                MATCH (p:ClinicalProtocol {id: $id})
                OPTIONAL MATCH (p)-[:HAS_MODULE]->(m:ProtocolModule)
                OPTIONAL MATCH (m)-[:HAS_STEP]->(s:ProtocolStep)
                OPTIONAL MATCH (p)-[:RECOMMENDS_OUTCOME]->(o:OutcomeMeasure)
                RETURN p, collect(DISTINCT m) AS modules, collect(DISTINCT s) AS steps, collect(DISTINCT o) AS outcomes
                """,
                id=protocol_id,
            ).single()
            if not rec:
                raise HTTPException(status_code=404, detail="Protocol not found")
            return {
                "protocol": dict(rec["p"]),
                "modules": [dict(m) for m in rec["modules"]],
                "steps": [dict(s) for s in rec["steps"]],
                "outcomes": [dict(o) for o in rec["outcomes"]],
            }
        raise HTTPException(status_code=404, detail="Protocol not found in memory")

    @router.post("/{protocol_id}/instantiate")
    def instantiate(request: Request, protocol_id: str, body: ProtocolInstanceRequest) -> Dict:
        ensure_role(request, allowed={"clinician", "researcher", "admin"})
        plan_id = instantiate_protocol(repo, protocol_id, participant_id=body.participant_id)
        modules: List[Dict] = []
        steps: List[Dict] = []
        if isinstance(repo, Neo4jMPGRepository):
            rec = repo.driver.session(database=repo.database).run(
                """
                MATCH (p:ClinicalProtocol {id: $id})-[:HAS_MODULE]->(m:ProtocolModule)
                OPTIONAL MATCH (m)-[:HAS_STEP]->(s:ProtocolStep)
                RETURN collect(DISTINCT m) AS modules, collect(DISTINCT s) AS steps
                """,
                id=protocol_id,
            ).single()
            modules = [dict(m) for m in rec["modules"]] if rec else []
            steps = [dict(s) for s in rec["steps"]] if rec else []
        instance = create_protocol_instance(
            repo,
            protocol_id,
            participant_id=body.participant_id,
            modules=modules,
            steps=steps,
            plan_id=plan_id,
        )
        return {"status": "created", "plan_id": plan_id, "protocol_instance_id": instance.id}

    @router.get("/instances")
    def list_protocol_instances(request: Request, participant_id: Optional[str] = None) -> List[Dict]:
        ensure_role(request, allowed={"clinician", "researcher", "admin"})
        return list_instances(repo, participant_id=participant_id)

    @router.post("/{instance_id}/scores")
    def update_scores(request: Request, instance_id: str, body: ScoreUpdateRequest) -> Dict:
        ensure_role(request, allowed={"clinician", "researcher", "admin"})
        if body.module_scores:
            update_module_state_scores(repo, instance_id, body.module_scores)
        if body.step_scores:
            update_step_state_scores(repo, body.step_scores)
        return {"status": "ok", "protocol_instance_id": instance_id}

    @router.post("/{instance_id}/auto_score")
    def auto_score(request: Request, instance_id: str) -> Dict:
        ensure_role(request, allowed={"clinician", "researcher", "admin"})
        module_scores = aggregator.module_scores_from_plan(instance_id)
        if module_scores:
            update_module_state_scores(repo, instance_id, module_scores)
        return {"status": "ok", "protocol_instance_id": instance_id, "module_scores": module_scores}

    return router
