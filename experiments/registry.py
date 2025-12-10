from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


class ExperimentRegistry:
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
            CREATE CONSTRAINT experiment_id IF NOT EXISTS FOR (e:Experiment) REQUIRE e.id IS UNIQUE;
            CREATE CONSTRAINT expt_condition_id IF NOT EXISTS FOR (c:ExperimentCondition) REQUIRE c.id IS UNIQUE;
            CREATE CONSTRAINT expt_run_id IF NOT EXISTS FOR (r:ExperimentRun) REQUIRE r.id IS UNIQUE;
            CREATE CONSTRAINT metricresult_id IF NOT EXISTS FOR (m:MetricResult) REQUIRE m.id IS UNIQUE;
            """
        )

    def create_experiment(self, name: str, description: str, prereg_link: Optional[str] = None) -> str:
        eid = str(uuid.uuid4())
        self.run(
            """
            CREATE (e:Experiment {
                id: $id,
                name: $name,
                description: $desc,
                prereg_link: $prereg,
                created_at: datetime()
            })
            """,
            id=eid,
            name=name,
            desc=description,
            prereg=prereg_link,
        )
        return eid

    def create_condition(self, experiment_id: str, name: str, stack: str, awareness_mode: str, notes: Optional[str] = None) -> str:
        cid = str(uuid.uuid4())
        self.run(
            """
            MATCH (e:Experiment {id: $eid})
            CREATE (c:ExperimentCondition {
                id: $cid,
                name: $name,
                stack: $stack,
                awareness_mode: $awareness,
                notes: coalesce($notes, "")
            })
            CREATE (e)-[:HAS_CONDITION]->(c)
            """,
            eid=experiment_id,
            cid=cid,
            name=name,
            stack=stack,
            awareness=awareness_mode,
            notes=notes,
        )
        return cid

    def create_run(self, condition_id: str, seed: int, n_trials: int) -> str:
        rid = str(uuid.uuid4())
        self.run(
            """
            MATCH (c:ExperimentCondition {id: $cid})
            CREATE (r:ExperimentRun {
                id: $rid,
                seed: $seed,
                n_trials: $n_trials,
                status: "RUNNING",
                started_at: datetime()
            })
            CREATE (c)-[:HAS_RUN]->(r)
            """,
            cid=condition_id,
            rid=rid,
            seed=seed,
            n_trials=n_trials,
        )
        return rid

    def finish_run(self, run_id: str, status: str = "COMPLETED") -> None:
        self.run(
            """
            MATCH (r:ExperimentRun {id: $rid})
            SET r.status = $status,
                r.ended_at = datetime()
            """,
            rid=run_id,
            status=status,
        )

    def add_metric(self, run_id: str, name: str, value: float, ci_lower: Optional[float] = None, ci_upper: Optional[float] = None, p_value: Optional[float] = None, details: Optional[Dict[str, Any]] = None) -> str:
        mid = str(uuid.uuid4())
        self.run(
            """
            MATCH (r:ExperimentRun {id: $rid})
            CREATE (m:MetricResult {
                id: $mid,
                name: $name,
                value: $value,
                ci_lower: $ci_lower,
                ci_upper: $ci_upper,
                p_value: $p_value,
                details: $details,
                created_at: datetime()
            })
            CREATE (r)-[:HAS_METRIC]->(m)
            """,
            rid=run_id,
            mid=mid,
            name=name,
            value=value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            details=details or {},
        )
        return mid
