from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Request

from api.authz import ensure_role
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from services.personalization import ProtocolPersonalizationEngine
from mpg.protocol_state import apply_adaptation


def build_adaptation_router(repo: Neo4jMPGRepository | InMemoryMPGRepository, ppe: ProtocolPersonalizationEngine) -> APIRouter:
    router = APIRouter(prefix="/clinical/adapt", tags=["adaptation"])

    @router.get("/suggestions")
    def suggestions(request: Request, protocol_instance_id: Optional[str] = None) -> List[Dict]:
        ensure_role(request, allowed={"clinician", "researcher", "admin"})
        # Placeholder: use module_confidence as score proxy
        recs: List[Dict] = []
        module_scores: Dict[str, float] = {}
        current_module_id: Optional[str] = None
        if isinstance(repo, Neo4jMPGRepository):
            result = repo.driver.session(database=repo.database).run(
                """
                MATCH (inst:ProtocolInstance)
                WHERE $pi IS NULL OR inst.id = $pi
                OPTIONAL MATCH (inst)-[:HAS_MODULE_STATE]->(ms:ModuleState)
                RETURN inst, collect(ms) AS modules
                """,
                pi=protocol_instance_id,
            )
            for row in result:
                inst = dict(row["inst"])
                current_module_id = inst.get("current_module_id")
                module_scores = {
                    m["module_id"]: m.get("coherence_delta_mean", 0.0) + m.get("symptom_delta_mean", 0.0)
                    for m in row["modules"]
                    if isinstance(m, dict)
                }
                suggestion = ppe.suggest(module_scores, current_module_id, inst.get("id"))
                if suggestion:
                    recs.append(
                        {
                            "protocol_instance_id": suggestion.protocol_instance_id,
                            "action": suggestion.suggested_action,
                            "target_module_id": suggestion.target_module_id,
                            "rationale": suggestion.rationale,
                        }
                    )
        return recs

    @router.post("/apply")
    def apply(request: Request, payload: Dict[str, str]) -> Dict:
        ensure_role(request, allowed={"clinician", "researcher", "admin"})
        pid = payload.get("protocol_instance_id")
        action = payload.get("action")
        target = payload.get("target_module_id")
        weight = payload.get("personalized_weight")
        if not pid or not action:
            return {"status": "error", "detail": "protocol_instance_id and action required"}
        weight_val = float(weight) if weight is not None else None
        apply_adaptation(repo, pid, action, target, personalized_weight=weight_val)
        return {"status": "ok", "protocol_instance_id": pid, "action": action}

    return router
