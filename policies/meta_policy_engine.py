from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


@dataclass
class PolicyVersionInfo:
    id: str
    trust_score: float
    status: str
    risk_tier: str


class MetaPolicyNeo4j:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def init_schema(self) -> None:
        statements = [
            "CREATE CONSTRAINT metapolicy_id IF NOT EXISTS FOR (m:MetaPolicy) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT policy_version_id IF NOT EXISTS FOR (v:PolicyVersion) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT policy_trustsnapshot_id IF NOT EXISTS FOR (t:PolicyTrustSnapshot) REQUIRE t.id IS UNIQUE",
        ]
        for stmt in statements:
            self.run(stmt)

    def ensure_meta_policy(self, meta_policy_id: str, name: str, scope: str = "INDIVIDUAL", risk_tier: str = "SAFE") -> None:
        self.run(
            """
            MERGE (m:MetaPolicy {id: $id})
            ON CREATE SET m.name = $name,
                          m.scope = $scope,
                          m.risk_tier = $risk_tier,
                          m.status = "ACTIVE",
                          m.created_at = datetime()
            ON MATCH SET m.updated_at = datetime()
            """,
            id=meta_policy_id,
            name=name,
            scope=scope,
            risk_tier=risk_tier,
        )

    def get_versions(self, meta_policy_id: str) -> List[PolicyVersionInfo]:
        records = self.run(
            """
            MATCH (m:MetaPolicy {id: $id})-[:HAS_VERSION]->(v:PolicyVersion)
            RETURN v.id AS id, coalesce(v.trust_score_latest, 0.0) AS trust, coalesce(v.status, "LIVE") AS status,
                   coalesce(m.risk_tier, "SAFE") AS risk
            """,
            id=meta_policy_id,
        )
        return [PolicyVersionInfo(id=r["id"], trust_score=float(r["trust"]), status=r["status"], risk_tier=r["risk"]) for r in records]

    def ensure_version_link(self, meta_policy_id: str, policy_version_id: str) -> None:
        self.run(
            """
            MATCH (m:MetaPolicy {id: $mid})
            MATCH (v:PolicyVersion {id: $vid})
            MERGE (m)-[:HAS_VERSION]->(v)
            """,
            mid=meta_policy_id,
            vid=policy_version_id,
        )

    def set_default_version(self, meta_policy_id: str, policy_version_id: str) -> None:
        self.run(
            """
            MATCH (m:MetaPolicy {id: $mid})
            MATCH (v:PolicyVersion {id: $vid})
            MERGE (m)-[r:DEFAULT_POLICY]->(v)
            """,
            mid=meta_policy_id,
            vid=policy_version_id,
        )

    def set_fallback_version(self, meta_policy_id: str, policy_version_id: str) -> None:
        self.run(
            """
            MATCH (m:MetaPolicy {id: $mid})
            MATCH (v:PolicyVersion {id: $vid})
            MERGE (m)-[r:FALLBACK_POLICY]->(v)
            """,
            mid=meta_policy_id,
            vid=policy_version_id,
        )


class MetaPolicyEngine:
    def __init__(self, meta_policy_id: str, default_version_id: str, fallback_version_id: Optional[str] = None, trust_threshold: float = 0.3):
        self.meta_policy_id = meta_policy_id
        self.db = MetaPolicyNeo4j()
        self.db.init_schema()
        self.db.ensure_meta_policy(meta_policy_id, name=meta_policy_id)
        self.db.ensure_version_link(meta_policy_id, default_version_id)
        self.db.set_default_version(meta_policy_id, default_version_id)
        if fallback_version_id:
            self.db.ensure_version_link(meta_policy_id, fallback_version_id)
            self.db.set_fallback_version(meta_policy_id, fallback_version_id)
        self.trust_threshold = trust_threshold

    def close(self) -> None:
        self.db.close()

    def select_version(self) -> str:
        versions = self.db.get_versions(self.meta_policy_id)
        live = [v for v in versions if v.status in ("LIVE", "CANDIDATE")]
        if not live:
            return self._fallback_version()
        # pick highest trust above threshold; else fallback
        live_sorted = sorted(live, key=lambda v: v.trust_score, reverse=True)
        if live_sorted[0].trust_score >= self.trust_threshold:
            return live_sorted[0].id
        return self._fallback_version()

    def _fallback_version(self) -> str:
        records = self.db.run(
            """
            MATCH (m:MetaPolicy {id: $id})-[:FALLBACK_POLICY]->(v:PolicyVersion)
            RETURN v.id AS vid
            """,
            id=self.meta_policy_id,
        )
        if records:
            return records[0]["vid"]
        return "NO_INTERVENTION"

    def spawn_candidate_version(self, parent_version_id: str, new_version_id: Optional[str] = None, version_tag: str = "candidate") -> str:
        vid = new_version_id or f"{parent_version_id}-{version_tag}-{uuid.uuid4().hex[:6]}"
        self.db.run(
            """
            MATCH (p:PolicyVersion {id: $parent})
            MERGE (v:PolicyVersion {id: $vid})
            ON CREATE SET v.policy_id = p.policy_id,
                          v.version_tag = $tag,
                          v.created_at = datetime(),
                          v.parent_version_id = $parent,
                          v.status = "CANDIDATE",
                          v.hyperparams = p.hyperparams,
                          v.context_dim = p.context_dim,
                          v.reasoning = "Spawned candidate"
            MERGE (m:MetaPolicy {id: $mid})
            MERGE (m)-[:HAS_VERSION]->(v)
            """,
            parent=parent_version_id,
            vid=vid,
            tag=version_tag,
            mid=self.meta_policy_id,
        )
        return vid

    def promote_version(self, version_id: str) -> None:
        self.db.run(
            """
            MATCH (v:PolicyVersion {id: $vid})
            SET v.status = "LIVE"
            """,
            vid=version_id,
        )
        self.db.set_default_version(self.meta_policy_id, version_id)

    def rollback_version(self, version_id: str) -> None:
        self.db.run(
            """
            MATCH (v:PolicyVersion {id: $vid})
            SET v.status = "ROLLED_BACK"
            """,
            vid=version_id,
        )
