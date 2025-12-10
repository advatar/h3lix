"""
CR-008: Compute PolicyTrustSnapshot and update PolicyVersion trust scores.

This demo job:
- Reads PolicyEpisode/PolicyOutcome grouped by PolicyVersion.
- Computes simple trust metrics (reward mean/std, overrides, delta coherence/accuracy).
- Writes PolicyTrustSnapshot and updates PolicyVersion.trust_score_latest.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List

from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


class TrustNeo4j:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def init_schema(self) -> None:
        self.run(
            """
            CREATE CONSTRAINT policy_trustsnapshot_id IF NOT EXISTS FOR (t:PolicyTrustSnapshot) REQUIRE t.id IS UNIQUE;
            """
        )

    def fetch_versions(self) -> List[Dict[str, Any]]:
        records = self.run("MATCH (v:PolicyVersion) RETURN v.id AS id")
        return [dict(r) for r in records]

    def fetch_metrics(self, version_id: str) -> Dict[str, Any]:
        records = self.run(
            """
            MATCH (v:PolicyVersion {id: $vid})-[:EVALUATED_IN]->(e:PolicyEpisode)
            OPTIONAL MATCH (e)-[:HAS_OUTCOME]->(o:PolicyOutcome)
            RETURN collect(o.reward) AS rewards,
                   collect(o.delta_coherence) AS dcs,
                   collect(o.delta_accuracy) AS das,
                   collect(o.delta_rt) AS drts,
                   collect(e) AS episodes
            """,
            vid=version_id,
        )
        if not records:
            return {}
        rec = records[0]
        return {k: rec[k] for k in rec.keys()}

    def write_trust_snapshot(
        self,
        version_id: str,
        t_value: float,
        reward_mean: float,
        reward_std: float,
        n_episodes: int,
        override_rate: float,
        delta_coherence_mean: float,
        delta_accuracy_mean: float,
        trust_score: float,
    ) -> None:
        tid = str(uuid.uuid4())
        self.run(
            """
            MATCH (v:PolicyVersion {id: $vid})
            CREATE (t:PolicyTrustSnapshot {
                id: $id,
                policy_version_id: $vid,
                t: $t,
                reward_mean: $rm,
                reward_std: $rs,
                n_episodes: $n,
                override_rate: $orate,
                delta_coherence_mean: $dc,
                delta_accuracy_mean: $da,
                trust_score: $ts,
                created_at: datetime()
            })
            CREATE (v)-[:HAS_TRUST_STATE]->(t)
            SET v.trust_score_latest = $ts
            """,
            id=tid,
            vid=version_id,
            t=t_value,
            rm=reward_mean,
            rs=reward_std,
            n=n_episodes,
            orate=override_rate,
            dc=delta_coherence_mean,
            da=delta_accuracy_mean,
            ts=trust_score,
        )


def safe_mean(vals: List[Any]) -> float:
    numeric = [float(v) for v in vals if v is not None]
    return sum(numeric) / len(numeric) if numeric else 0.0


def safe_std(vals: List[Any]) -> float:
    numeric = [float(v) for v in vals if v is not None]
    if len(numeric) < 2:
        return 0.0
    mean = sum(numeric) / len(numeric)
    var = sum((v - mean) ** 2 for v in numeric) / (len(numeric) - 1)
    return var ** 0.5


def compute_trust_score(reward_mean: float, reward_std: float, override_rate: float, delta_coh: float, n_episodes: int) -> float:
    # Simple normalized score prioritizing safety/robustness
    reward_component = max(0.0, min(1.0, 0.5 + reward_mean))  # assume reward bounded ~[-1,1]
    stability_component = max(0.0, 1.0 - min(1.0, reward_std))
    safety_component = max(0.0, 1.0 - override_rate)
    coherence_component = max(0.0, min(1.0, 0.5 + delta_coh))
    volume_component = max(0.0, min(1.0, n_episodes / 20.0))
    trust = (
        0.25 * safety_component
        + 0.2 * stability_component
        + 0.2 * reward_component
        + 0.2 * coherence_component
        + 0.15 * volume_component
    )
    return float(max(0.0, min(1.0, trust)))


def main() -> None:
    db = TrustNeo4j()
    try:
        db.init_schema()
        versions = db.fetch_versions()
        if not versions:
            print("No PolicyVersion nodes found.")
            return
        t_value = time.time()
        for v in versions:
            vid = v["id"]
            metrics = db.fetch_metrics(vid)
            if not metrics:
                continue
            rewards = metrics.get("rewards", [])
            episodes = metrics.get("episodes", [])
            n_episodes = len(episodes)
            reward_mean = safe_mean(rewards)
            reward_std = safe_std(rewards)
            override_rate = 0.0  # placeholders; override flags can be added later
            delta_coh_mean = safe_mean(metrics.get("dcs", []))
            delta_acc_mean = safe_mean(metrics.get("das", []))
            trust_score = compute_trust_score(reward_mean, reward_std, override_rate, delta_coh_mean, n_episodes)
            db.write_trust_snapshot(
                version_id=vid,
                t_value=t_value,
                reward_mean=reward_mean,
                reward_std=reward_std,
                n_episodes=n_episodes,
                override_rate=override_rate,
                delta_coherence_mean=delta_coh_mean,
                delta_accuracy_mean=delta_acc_mean,
                trust_score=trust_score,
            )
            print(f"Updated trust for {vid}: trust_score={trust_score:.3f}, n={n_episodes}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
