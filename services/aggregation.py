from __future__ import annotations

from typing import Dict, List, Tuple

from mpg.repository import Neo4jMPGRepository, InMemoryMPGRepository


class ProtocolScoreAggregator:
    """Aggregates coarse module/step scores from SegmentState and Trial data."""

    def __init__(self, repo: Neo4jMPGRepository | InMemoryMPGRepository):
        self.repo = repo

    def module_scores_from_plan(self, protocol_instance_id: str) -> Dict[str, Dict[str, float]]:
        """
        For Neo4j: collect target segments from plan, average SegmentState coherence/potency deltas
        and map to all modules as a coarse signal.
        """
        if isinstance(self.repo, InMemoryMPGRepository):
            return {}
        with self.repo.driver.session(database=self.repo.database) as session:
            rec = session.run(
                """
                MATCH (pi:ProtocolInstance {id: $pid})
                OPTIONAL MATCH (pi)-[:USES_PLAN]->(ip:InterventionPlan)-[:TARGETS_SEGMENT]->(s:Segment)
                OPTIONAL MATCH (s)-[:HAS_STATE]->(st:SegmentState)
                WITH pi, collect(distinct s.id) AS segments, collect(st) AS states
                OPTIONAL MATCH (pi)-[:HAS_MODULE_STATE]->(ms:ModuleState)
                RETURN pi, segments, states, collect(ms) AS modules
                """,
                pid=protocol_instance_id,
            ).single()
            if not rec:
                return {}
            states = [dict(st) for st in rec["states"] if st]
            modules = [dict(ms) for ms in rec["modules"] if ms]
            coherence_vals = [st.get("coherence") for st in states if st.get("coherence") is not None]
            potency_vals = [st.get("potency") for st in states if st.get("potency") is not None]
            coherence_avg = float(sum(coherence_vals) / len(coherence_vals)) if coherence_vals else 0.0
            potency_avg = float(sum(potency_vals) / len(potency_vals)) if potency_vals else 0.0
            module_scores: Dict[str, Dict[str, float]] = {}
            for m in modules:
                mid = m.get("module_id")
                if not mid:
                    continue
                module_scores[mid] = {
                    "coherence_delta_mean": coherence_avg,
                    "symptom_delta_mean": 0.0,
                    "rv_potency_delta_mean": -potency_avg,
                }
            return module_scores

    def step_scores_placeholder(self) -> Dict[str, Dict[str, float]]:
        return {}
