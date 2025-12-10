from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository


@dataclass
class ProtocolTemplate:
    id: str
    name: str
    target_condition: str
    description: str
    sorkn_focus: Dict[str, List[str]]
    risk_tier: str = "LOW"
    status: str = "TEMPLATE"


@dataclass
class ProtocolModule:
    id: str
    protocol_id: str
    name: str
    order_index: int
    description: str
    goal_summary: str
    duration_sessions_estimate: Optional[int] = None


@dataclass
class ProtocolStep:
    id: str
    module_id: str
    name: str
    step_type: str
    kmp_task_template_id: Optional[str] = None
    suggested_repetitions: int = 1
    notes_for_clinician: Optional[str] = None


@dataclass
class OutcomeMeasure:
    id: str
    name: str
    domain: str
    scale_type: str
    collection_mode: str
    target_frequency: str


def load_protocol_template(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    template: ProtocolTemplate,
    modules: List[ProtocolModule],
    steps: List[ProtocolStep],
    outcomes: List[OutcomeMeasure],
) -> None:
    if isinstance(repo, Neo4jMPGRepository):
        driver = repo.driver
        with driver.session(database=repo.database) as session:
            session.run(
                """
                MERGE (p:ClinicalProtocol {id: $id})
                SET p.name = $name,
                    p.target_condition = $cond,
                    p.description = $desc,
                    p.sorkn_focus = $sorkn,
                    p.risk_tier = $risk,
                    p.status = $status
                """,
                id=template.id,
                name=template.name,
                cond=template.target_condition,
                desc=template.description,
                sorkn=template.sorkn_focus,
                risk=template.risk_tier,
                status=template.status,
            )
            for mod in modules:
                session.run(
                    """
                    MATCH (p:ClinicalProtocol {id: $pid})
                    MERGE (m:ProtocolModule {id: $id})
                    SET m.name = $name,
                        m.order_index = $idx,
                        m.description = $desc,
                        m.goal_summary = $goal,
                        m.duration_sessions_estimate = $dur
                    MERGE (p)-[:HAS_MODULE]->(m)
                    """,
                    pid=template.id,
                    id=mod.id,
                    name=mod.name,
                    idx=mod.order_index,
                    desc=mod.description,
                    goal=mod.goal_summary,
                    dur=mod.duration_sessions_estimate,
                )
            for step in steps:
                session.run(
                    """
                    MATCH (m:ProtocolModule {id: $mid})
                    MERGE (s:ProtocolStep {id: $id})
                    SET s.name = $name,
                        s.step_type = $stype,
                        s.kmp_task_template_id = $task,
                        s.suggested_repetitions = $rep,
                        s.notes_for_clinician = $notes
                    MERGE (m)-[:HAS_STEP]->(s)
                    """,
                    mid=step.module_id,
                    id=step.id,
                    name=step.name,
                    stype=step.step_type,
                    task=step.kmp_task_template_id,
                    rep=step.suggested_repetitions,
                    notes=step.notes_for_clinician,
                )
            for om in outcomes:
                session.run(
                    """
                    MATCH (p:ClinicalProtocol {id: $pid})
                    MERGE (o:OutcomeMeasure {id: $id})
                    SET o.name = $name,
                        o.domain = $dom,
                        o.scale_type = $scale,
                        o.collection_mode = $mode,
                        o.target_frequency = $freq
                    MERGE (p)-[:RECOMMENDS_OUTCOME]->(o)
                    """,
                    pid=template.id,
                    id=om.id,
                    name=om.name,
                    dom=om.domain,
                    scale=om.scale_type,
                    mode=om.collection_mode,
                    freq=om.target_frequency,
                )
    else:
        repo.nodes[template.id] = template  # type: ignore[index]
        for mod in modules:
            repo.nodes[mod.id] = mod  # type: ignore[index]
        for step in steps:
            repo.nodes[step.id] = step  # type: ignore[index]
        for om in outcomes:
            repo.nodes[om.id] = om  # type: ignore[index]


def instantiate_protocol(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    protocol_id: str,
    participant_id: str,
    plan_id: Optional[str] = None,
) -> str:
    plan_id = plan_id or str(uuid.uuid4())
    if isinstance(repo, Neo4jMPGRepository):
        repo.driver.session(database=repo.database).run(
            """
            MATCH (p:ClinicalProtocol {id: $pid}), (pt:Participant {id: $participant})
            MERGE (ip:InterventionPlan {id: $plan})
            SET ip.name = p.name + " plan",
                ip.type = "PROTOCOL",
                ip.protocol_id = p.id,
                ip.participant_id = pt.id
            MERGE (pt)-[:HAS_PLAN]->(ip)
            MERGE (ip)-[:FOLLOWS_PROTOCOL]->(p)
            WITH p, ip
            MATCH (p)-[:HAS_MODULE]->(m:ProtocolModule)
            MERGE (ip)-[:USES_MODULE]->(m)
            WITH ip, m
            MATCH (m)-[:HAS_STEP]->(s:ProtocolStep)
            MERGE (ip)-[:USES_STEP]->(s)
            """,
            pid=protocol_id,
            participant=participant_id,
            plan=plan_id,
        )
    else:
        repo.nodes[plan_id] = {
            "id": plan_id,
            "protocol_id": protocol_id,
            "participant_id": participant_id,
            "type": "PROTOCOL",
        }  # type: ignore[index]
    return plan_id
