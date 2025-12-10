from __future__ import annotations

import hashlib
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import json
from neo4j import GraphDatabase

from policies.contextual_bandit import ActionDef, LinearUCBBandit

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


class PolicyNeo4j:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def init_schema(self) -> None:
        statements = [
            "CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT policy_episode_id IF NOT EXISTS FOR (e:PolicyEpisode) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT policy_outcome_id IF NOT EXISTS FOR (o:PolicyOutcome) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT intervention_type_id IF NOT EXISTS FOR (i:InterventionType) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT policy_version_id IF NOT EXISTS FOR (v:PolicyVersion) REQUIRE v.id IS UNIQUE",
        ]
        for stmt in statements:
            self.run(stmt)

    def ensure_interventions(self, interventions: List[ActionDef]) -> None:
        for a in interventions:
            params_json = json.dumps(a.params_template or {})
            self.run(
                """
                MERGE (i:InterventionType {id: $id})
                SET i.name = $name,
                    i.layer_target = coalesce(i.layer_target, "Symbolic"),
                    i.risk_level = coalesce(i.risk_level, "LOW"),
                    i.description = coalesce(i.description, ""),
                    i.parameters_schema = coalesce(i.parameters_schema, $params_json),
                i.active = true
                """,
                id=a.id,
                name=a.name,
                params_json=params_json,
            )

    def ensure_policy_version(self, policy_version_id: str, policy_id: str, version_tag: str, hyperparams: Dict[str, Any], context_dim: int) -> None:
        hyperparams_json = json.dumps(hyperparams or {})
        self.run(
            """
            MERGE (v:PolicyVersion {id: $vid})
            ON CREATE SET v.policy_id = $pid,
                          v.version_tag = $tag,
                          v.created_at = datetime(),
                          v.status = "LIVE",
                          v.hyperparams = $hyperparams_json,
                          v.context_dim = $context_dim,
                          v.reasoning = "Auto-created default version"
            WITH v
            MERGE (p:Policy {id: $pid})
            MERGE (v)-[:OF_POLICY]->(p)
            """,
            vid=policy_version_id,
            pid=policy_id,
            tag=version_tag,
            hyperparams_json=hyperparams_json,
            context_dim=context_dim,
        )

    def create_episode(
        self,
        policy_id: str,
        policy_version_id: str,
        trial_id: str,
        context_hash: str,
        rv_segment_ids: List[str],
        collective_segment_ids: List[str],
        chosen_intervention_id: str,
        parameters: Dict[str, Any],
    ) -> str:
        eid = str(uuid.uuid4())
        self.run(
            """
            MATCH (p:Policy {id: $pid})
            MATCH (t:Trial {id: $tid})
            CREATE (e:PolicyEpisode {
                id: $eid,
                context_hash: $ctx_hash,
                policy_version_id: $pvid,
                rv_segment_ids: $rv_ids,
                collective_segment_ids: $cs_ids,
                chosen_intervention_id: $intervention_id,
                parameters: $parameters,
                human_override: false,
                timestamp: datetime()
            })
            CREATE (p)-[:HAS_EPISODE]->(e)
            CREATE (e)-[:FOR_TRIAL]->(t)
            WITH e
            MATCH (v:PolicyVersion {id: $pvid})
            MERGE (v)-[:EVALUATED_IN]->(e)
            """,
            pid=policy_id,
            tid=trial_id,
            eid=eid,
            ctx_hash=context_hash,
            pvid=policy_version_id,
            rv_ids=rv_segment_ids,
            cs_ids=collective_segment_ids,
            intervention_id=chosen_intervention_id,
            parameters=parameters,
        )
        return eid

    def create_outcome(
        self,
        episode_id: str,
        reward: float,
        delta_coherence: Optional[float],
        delta_accuracy: Optional[float],
        delta_rt: Optional[float],
        notes: str = "",
        human_override: bool = False,
        override_type: Optional[str] = None,
    ) -> str:
        oid = str(uuid.uuid4())
        self.run(
            """
            MATCH (e:PolicyEpisode {id: $eid})
            CREATE (o:PolicyOutcome {
                id: $oid,
                reward: $reward,
                delta_coherence: $dc,
                delta_accuracy: $da,
                delta_rt: $drt,
                notes: $notes,
                human_override: $hov,
                override_type: $otype
            })
            CREATE (e)-[:HAS_OUTCOME]->(o)
            """,
            eid=episode_id,
            oid=oid,
            reward=reward,
            dc=delta_coherence,
            da=delta_accuracy,
            drt=delta_rt,
            notes=notes,
            hov=human_override,
            otype=override_type,
        )
        return oid


class PolicyEngine:
    def __init__(
        self,
        actions: List[ActionDef],
        context_dim: int,
        alpha: float = 1.0,
        policy_id: str = "policy-demo",
        policy_version_id: Optional[str] = None,
        version_tag: str = "v1",
        hyperparams: Optional[Dict[str, Any]] = None,
    ):
        self.bandit = LinearUCBBandit(actions, d=context_dim, alpha=alpha)
        self.actions = actions
        self.context_dim = context_dim
        self.policy_id = policy_id
        self.policy_version_id = policy_version_id or f"{policy_id}-{version_tag}"
        self.db = PolicyNeo4j()
        self.db.init_schema()
        self.db.ensure_interventions(actions)
        self._ensure_policy(policy_id)
        self.db.ensure_policy_version(
            policy_version_id=self.policy_version_id,
            policy_id=self.policy_id,
            version_tag=version_tag,
            hyperparams=hyperparams or {"alpha": alpha},
            context_dim=context_dim,
        )

    def close(self) -> None:
        self.db.close()

    def _ensure_policy(self, policy_id: str) -> None:
        self.db.run(
            """
            MERGE (p:Policy {id: $id})
            ON CREATE SET p.name = $id, p.description = "Demo policy", p.version = "v1"
            """,
            id=policy_id,
        )

    @staticmethod
    def context_hash(x: np.ndarray) -> str:
        return hashlib.sha256(x.tobytes()).hexdigest()

    def recommend(
        self,
        trial_id: str,
        x: np.ndarray,
        rv_segment_ids: List[str],
        collective_segment_ids: List[str],
    ) -> Tuple[ActionDef, str]:
        action = self.bandit.select_action(x)
        ctx_hash = self.context_hash(x)
        episode_id = self.db.create_episode(
            policy_id=self.policy_id,
            policy_version_id=self.policy_version_id,
            trial_id=trial_id,
            context_hash=ctx_hash,
            rv_segment_ids=rv_segment_ids,
            collective_segment_ids=collective_segment_ids,
            chosen_intervention_id=action.id,
            parameters=action.params_template,
        )
        return action, episode_id

    def update(self, x: np.ndarray, episode_id: str, action_id: str, reward: float, delta_coherence: Optional[float] = None, delta_accuracy: Optional[float] = None, delta_rt: Optional[float] = None, notes: str = "", human_override: bool = False, override_type: Optional[str] = None) -> None:
        self.bandit.update(x, action_id, reward)
        self.db.create_outcome(
            episode_id=episode_id,
            reward=reward,
            delta_coherence=delta_coherence,
            delta_accuracy=delta_accuracy,
            delta_rt=delta_rt,
            notes=notes,
            human_override=human_override,
            override_type=override_type,
        )
