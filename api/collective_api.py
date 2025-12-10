from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import APIRouter
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


class CollectiveNeo4j:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def get_collective_segments(self) -> List[Dict[str, Any]]:
        records = self.run("MATCH (c:CollectiveSegment) RETURN c")
        return [dict(r["c"]) for r in records]

    def get_collective_rv(self) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (c:CollectiveSegment)
            WHERE coalesce(c.rv, false) = true
            RETURN c
            """
        )
        return [dict(r["c"]) for r in records]

    def get_group_coherence_series(self, group_session_id: str) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (:GroupSession {id: $id})-[:HAS_GROUP_TRIAL]->(gt:GroupTrial)
            RETURN gt.id AS group_trial_id, gt.coherence AS coherence
            ORDER BY gt.id
            """,
            id=group_session_id,
        )
        return [dict(r) for r in records]

    def get_group_trial(self, group_trial_id: str) -> Dict[str, Any]:
        records = self.run(
            """
            MATCH (gt:GroupTrial {id: $id})
            OPTIONAL MATCH (gt)-[:ALIGNS_TRIAL]->(t:Trial)
            RETURN gt, collect(t) AS trials
            """,
            id=group_trial_id,
        )
        if not records:
            return {}
        rec = records[0]
        out = dict(rec["gt"])
        out["aligned_trials"] = [dict(t) for t in rec["trials"] if t]
        return out


db = CollectiveNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
router = APIRouter(prefix="/collective", tags=["collective"])


@router.get("/segments")
def list_collective_segments() -> List[Dict[str, Any]]:
    return db.get_collective_segments()


@router.get("/segments/rv")
def list_collective_rv() -> List[Dict[str, Any]]:
    return db.get_collective_rv()


@router.get("/coherence/{group_session_id}")
def group_coherence_series(group_session_id: str) -> List[Dict[str, Any]]:
    return db.get_group_coherence_series(group_session_id)


@router.get("/trials/{group_trial_id}")
def group_trial_detail(group_trial_id: str) -> Dict[str, Any]:
    return db.get_group_trial(group_trial_id)
