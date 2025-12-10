from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from policies.meta_policy_engine import MetaPolicyNeo4j, MetaPolicyEngine

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")

db = MetaPolicyNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
db.init_schema()

router = APIRouter(prefix="/meta_policy", tags=["meta_policy"])


@router.get("/{meta_policy_id}/status")
def get_meta_policy_status(meta_policy_id: str) -> Dict[str, Any]:
    versions = db.get_versions(meta_policy_id)
    if not versions:
        raise HTTPException(status_code=404, detail="MetaPolicy not found or has no versions")
    records = db.run(
        """
        MATCH (m:MetaPolicy {id: $id})-[:DEFAULT_POLICY]->(v:PolicyVersion)
        OPTIONAL MATCH (m)-[:FALLBACK_POLICY]->(f:PolicyVersion)
        RETURN v.id AS default_version, f.id AS fallback_version
        """,
        id=meta_policy_id,
    )
    default_version = records[0]["default_version"] if records else None
    fallback_version = records[0]["fallback_version"] if records else None
    return {
        "meta_policy": meta_policy_id,
        "default_version": default_version,
        "fallback_version": fallback_version,
        "versions": [v.__dict__ for v in versions],
    }


@router.get("/{meta_policy_id}/versions")
def list_versions(meta_policy_id: str) -> List[Dict[str, Any]]:
    versions = db.get_versions(meta_policy_id)
    return [v.__dict__ for v in versions]


class VersionControl(BaseModel):
    meta_policy_id: str
    version_id: str
    action: str  # PROMOTE | ROLLBACK | SET_FALLBACK


@router.post("/version_control")
def version_control(vc: VersionControl) -> Dict[str, Any]:
    engine = MetaPolicyEngine(meta_policy_id=vc.meta_policy_id, default_version_id=vc.version_id)
    try:
        if vc.action == "PROMOTE":
            engine.promote_version(vc.version_id)
        elif vc.action == "ROLLBACK":
            engine.rollback_version(vc.version_id)
        elif vc.action == "SET_FALLBACK":
            engine.db.set_fallback_version(vc.meta_policy_id, vc.version_id)
        else:
            raise HTTPException(status_code=400, detail="Unknown action")
        return {"status": "ok"}
    finally:
        engine.close()
