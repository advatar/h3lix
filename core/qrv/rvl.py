from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from core.qrv.models import RogueEventRecord


class RogueVariableLibrary:
    def __init__(
        self,
        repo: Neo4jMPGRepository | InMemoryMPGRepository,
        audit_path: Path | None = None,
    ):
        self.repo = repo
        self.audit_path = audit_path or Path("results/qrvm_rvl.parquet")
        self._in_memory: List[RogueEventRecord] = []

    def _write_audit(self, record: RogueEventRecord) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(
            [
                {
                    "id": record.id,
                    "session_id": record.session_id,
                    "t_rel_ms": record.t_rel_ms,
                    "rogue_segments": ",".join(record.detection.rogue_segments),
                    "error_norm": record.detection.error_norm,
                    "ablation_improvement": record.detection.ablation_improvement,
                    "prompt_id": record.prompt_id,
                    "pre_basis": ",".join(record.detection.pre_state.basis) if record.detection.pre_state else "",
                    "post_basis": ",".join(record.detection.post_state.basis) if record.detection.post_state else "",
                    "pre_amplitudes": record.detection.pre_state.amplitudes if record.detection.pre_state else [],
                    "post_amplitudes": record.detection.post_state.amplitudes if record.detection.post_state else [],
                }
            ]
        )
        if self.audit_path.exists():
            existing = pd.read_parquet(self.audit_path)
            df = pd.concat([existing, df], ignore_index=True)
        df.to_parquet(self.audit_path, index=False)

    def _persist_neo4j(self, record: RogueEventRecord) -> None:
        if not isinstance(self.repo, Neo4jMPGRepository):
            return
        driver = self.repo.driver
        with driver.session(database=self.repo.database) as session:
            session.run(
                """
                MERGE (e:RogueEvent {id: $id})
                SET e.session_id = $session_id,
                    e.t_rel_ms = $t_rel_ms,
                    e.error_norm = $error_norm,
                    e.ablation_improvement = $improvement,
                    e.rogue_segments = $segments,
                    e.prompt_id = $prompt_id,
                    e.source = "qrvm_spectral",
                    e.created_at = datetime()
                """,
                id=record.id,
                session_id=record.session_id,
                t_rel_ms=record.t_rel_ms,
                error_norm=record.detection.error_norm,
                improvement=record.detection.ablation_improvement,
                segments=record.detection.rogue_segments,
                prompt_id=record.prompt_id,
            )
            # Store pre/post QMS as separate nodes for retrieval
            if record.detection.pre_state:
                session.run(
                    """
                    MERGE (q:QMSState {id: $qid})
                    SET q.basis = $basis,
                        q.amplitudes = $amps,
                        q.norm = $norm,
                        q.session_id = $session_id,
                        q.t_rel_ms = $t_rel_ms
                    WITH q
                    MATCH (e:RogueEvent {id: $eid})
                    MERGE (e)-[:HAS_PRE_STATE]->(q)
                    """,
                    qid=f"{record.id}_pre",
                    basis=record.detection.pre_state.basis,
                    amps=[float(abs(a)) for a in record.detection.pre_state.amplitudes],
                    norm=record.detection.pre_state.norm,
                    session_id=record.session_id,
                    t_rel_ms=record.t_rel_ms,
                    eid=record.id,
                )
            if record.detection.post_state:
                session.run(
                    """
                    MERGE (q:QMSState {id: $qid})
                    SET q.basis = $basis,
                        q.amplitudes = $amps,
                        q.norm = $norm,
                        q.session_id = $session_id,
                        q.t_rel_ms = $t_rel_ms
                    WITH q
                    MATCH (e:RogueEvent {id: $eid})
                    MERGE (e)-[:HAS_POST_STATE]->(q)
                    """,
                    qid=f"{record.id}_post",
                    basis=record.detection.post_state.basis,
                    amps=[float(abs(a)) for a in record.detection.post_state.amplitudes],
                    norm=record.detection.post_state.norm,
                    session_id=record.session_id,
                    t_rel_ms=record.t_rel_ms,
                    eid=record.id,
                )
            for direction in record.detection.rogue_directions:
                session.run(
                    """
                    MERGE (d:RogueDirection {id: $did})
                    SET d.eigenvalue = $eig, d.loadings = $loadings, d.delta_error = $delta
                    WITH d
                    MATCH (e:RogueEvent {id: $eid})
                    MERGE (e)-[:HAS_DIRECTION]->(d)
                    """,
                    did=direction.direction_id,
                    eig=direction.eigenvalue,
                    loadings=direction.loadings,
                    delta=direction.delta_error,
                    eid=record.id,
                )
                for seg in direction.high_segments:
                    session.run(
                        """
                        MATCH (d:RogueDirection {id: $did})
                        MATCH (s {id: $sid})
                        MERGE (d)-[:INVOLVES]->(s)
                        """,
                        did=direction.direction_id,
                        sid=seg,
                    )

    def record(self, record: RogueEventRecord) -> None:
        self._in_memory.append(record)
        self._write_audit(record)
        self._persist_neo4j(record)

    def list_events(self, session_id: Optional[str] = None) -> List[Dict]:
        events = []
        for rec in self._in_memory:
            if session_id and rec.session_id != session_id:
                continue
            events.append(rec.model_dump())
        if isinstance(self.repo, Neo4jMPGRepository):
            driver = self.repo.driver
            with driver.session(database=self.repo.database) as session:
                query = """
                MATCH (e:RogueEvent)
                WHERE $sid IS NULL OR e.session_id = $sid
                RETURN e
                ORDER BY e.t_rel_ms ASC
                """
                for row in session.run(query, sid=session_id):
                    events.append(dict(row["e"]))
        return events
