from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository


@dataclass
class ProtocolInstance:
    id: str
    protocol_id: str
    participant_id: str
    plan_id: Optional[str]
    start_date: float
    status: str = "ACTIVE"
    current_module_id: Optional[str] = None
    progress_index: float = 0.0
    risk_tier: str = "LOW"


@dataclass
class ModuleState:
    id: str
    protocol_instance_id: str
    module_id: str
    status: str = "NOT_STARTED"
    sessions_completed: int = 0
    steps_completed: int = 0
    personalized_weight: float = 1.0
    coherence_delta_mean: float = 0.0
    symptom_delta_mean: float = 0.0
    rv_potency_delta_mean: float = 0.0
    last_review_time: float = 0.0


@dataclass
class StepState:
    id: str
    module_state_id: str
    step_id: str
    status: str = "NOT_ASSIGNED"
    assignments_count: int = 0
    completed_count: int = 0
    last_outcome_score: float = 0.0
    coherence_effect: float = 0.0
    rv_effect: float = 0.0
    user_burden_score: float = 0.0


def create_protocol_instance(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    protocol_id: str,
    participant_id: str,
    modules: List[Dict],
    steps: List[Dict],
    plan_id: Optional[str] = None,
) -> ProtocolInstance:
    instance = ProtocolInstance(
        id=str(uuid.uuid4()),
        protocol_id=protocol_id,
        participant_id=participant_id,
        plan_id=plan_id,
        start_date=time.time(),
        status="ACTIVE",
        current_module_id=modules[0]["id"] if modules else None,
        risk_tier="LOW",
    )
    module_states = [
        ModuleState(
            id=str(uuid.uuid4()),
            protocol_instance_id=instance.id,
            module_id=m["id"],
            status="NOT_STARTED",
            last_review_time=time.time(),
        )
        for m in modules
    ]
    step_states: List[StepState] = []
    for st in steps:
        # find module mapping
        ms = next((ms for ms in module_states if ms.module_id == st.get("module_id")), None)
        if not ms:
            continue
        step_states.append(
            StepState(
                id=str(uuid.uuid4()),
                module_state_id=ms.id,
                step_id=st["id"],
                status="NOT_ASSIGNED",
            )
        )
    if isinstance(repo, Neo4jMPGRepository):
        with repo.driver.session(database=repo.database) as session:
            session.run(
                """
                MATCH (p:ClinicalProtocol {id: $pid}), (participant:Participant {id: $participant})
                MERGE (inst:ProtocolInstance {id: $id})
                SET inst.protocol_id = p.id,
                    inst.participant_id = participant.id,
                    inst.start_date = datetime({epochSeconds: $start}),
                    inst.status = $status,
                inst.current_module_id = $current_module_id,
                inst.progress_index = $progress,
                inst.risk_tier = $risk,
                inst.plan_id = $plan_id
            MERGE (p)-[:INSTANTIATED_AS]->(inst)
            MERGE (participant)-[:ASSIGNED_PROTOCOL]->(inst)
            WITH inst
            OPTIONAL MATCH (ip:InterventionPlan {id: $plan_id})
            MERGE (inst)-[:USES_PLAN]->(ip)
            """,
            pid=protocol_id,
            participant=participant_id,
            id=instance.id,
            start=instance.start_date,
            status=instance.status,
            current_module_id=instance.current_module_id,
            progress=instance.progress_index,
            risk=instance.risk_tier,
            plan_id=instance.plan_id,
        )
            for ms in module_states:
                session.run(
                    """
                    MATCH (inst:ProtocolInstance {id: $inst_id})
                    MATCH (m:ProtocolModule {id: $module_id})
                    MERGE (ms:ModuleState {id: $id})
                    SET ms.status = $status,
                        ms.sessions_completed = $sessions_completed,
                        ms.steps_completed = $steps_completed,
                        ms.personalized_weight = $personalized_weight,
                        ms.coherence_delta_mean = $coh,
                        ms.symptom_delta_mean = $sym,
                        ms.rv_potency_delta_mean = $rv,
                        ms.last_review_time = datetime({epochSeconds: $last_review})
                    MERGE (inst)-[:HAS_MODULE_STATE]->(ms)
                    MERGE (m)-[:TEMPLATE_FOR]->(ms)
                    """,
                    inst_id=instance.id,
                    module_id=ms.module_id,
                    id=ms.id,
                    status=ms.status,
                    sessions_completed=ms.sessions_completed,
                    steps_completed=ms.steps_completed,
                    personalized_weight=ms.personalized_weight,
                    coh=ms.coherence_delta_mean,
                    sym=ms.symptom_delta_mean,
                    rv=ms.rv_potency_delta_mean,
                    last_review=ms.last_review_time,
                )
            for ss in step_states:
                session.run(
                    """
                    MATCH (ms:ModuleState {id: $msid})
                    MATCH (st:ProtocolStep {id: $step_id})
                    MERGE (ss:StepState {id: $id})
                    SET ss.status = $status,
                        ss.assignments_count = $assign,
                        ss.completed_count = $completed,
                        ss.last_outcome_score = $score,
                        ss.coherence_effect = $coh,
                        ss.rv_effect = $rv,
                        ss.user_burden_score = $burden
                    MERGE (ms)-[:HAS_STEP_STATE]->(ss)
                    MERGE (st)-[:TEMPLATE_FOR]->(ss)
                    """,
                    msid=ss.module_state_id,
                    step_id=ss.step_id,
                    id=ss.id,
                    status=ss.status,
                    assign=ss.assignments_count,
                    completed=ss.completed_count,
                    score=ss.last_outcome_score,
                    coh=ss.coherence_effect,
                    rv=ss.rv_effect,
                    burden=ss.user_burden_score,
                )
    else:
        repo.nodes[instance.id] = instance  # type: ignore[index]
        for ms in module_states:
            repo.nodes[ms.id] = ms  # type: ignore[index]
        for ss in step_states:
            repo.nodes[ss.id] = ss  # type: ignore[index]
    return instance


def list_instances(repo: Neo4jMPGRepository | InMemoryMPGRepository, participant_id: Optional[str] = None) -> List[Dict]:
    if isinstance(repo, Neo4jMPGRepository):
        with repo.driver.session(database=repo.database) as session:
            recs = session.run(
                """
                MATCH (inst:ProtocolInstance)
                WHERE $pid IS NULL OR inst.participant_id = $pid
                RETURN inst
                """,
                pid=participant_id,
            )
            return [dict(r["inst"]) for r in recs]
    instances: List[Dict] = []
    for node in repo.nodes.values():  # type: ignore[union-attr]
        if isinstance(node, ProtocolInstance):
            if participant_id is None or node.participant_id == participant_id:
                instances.append(
                    {
                        "id": node.id,
                        "protocol_id": node.protocol_id,
                        "participant_id": node.participant_id,
                        "status": node.status,
                        "current_module_id": node.current_module_id,
                    }
                )
    return instances


def apply_adaptation(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    protocol_instance_id: str,
    action: str,
    target_module_id: Optional[str],
    personalized_weight: Optional[float] = None,
) -> None:
    weight = personalized_weight if personalized_weight is not None else 1.0
    if isinstance(repo, Neo4jMPGRepository):
        with repo.driver.session(database=repo.database) as session:
            if action == "advance" and target_module_id:
                session.run(
                    """
                    MATCH (inst:ProtocolInstance {id: $pid})
                    SET inst.current_module_id = $mid, inst.progress_index = inst.progress_index + 0.1
                    """,
                    pid=protocol_instance_id,
                    mid=target_module_id,
                )
            if target_module_id:
                session.run(
                    """
                    MATCH (:ProtocolInstance {id: $pid})-[:HAS_MODULE_STATE]->(ms:ModuleState {module_id: $mid})
                    SET ms.personalized_weight = $w
                    """,
                    pid=protocol_instance_id,
                    mid=target_module_id,
                    w=weight,
                )
    else:
        inst = repo.nodes.get(protocol_instance_id)  # type: ignore[index]
        if isinstance(inst, ProtocolInstance):
            if action == "advance" and target_module_id:
                inst.current_module_id = target_module_id
                inst.progress_index += 0.1
            repo.nodes[protocol_instance_id] = inst  # type: ignore[index]
        for node_id, node in repo.nodes.items():  # type: ignore[union-attr]
            if isinstance(node, ModuleState) and node.protocol_instance_id == protocol_instance_id and node.module_id == target_module_id:
                node.personalized_weight = weight
                repo.nodes[node_id] = node  # type: ignore[index]


def update_module_state_scores(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    protocol_instance_id: str,
    module_scores: Dict[str, Dict[str, float]],
) -> None:
    """
    module_scores: {module_id: {"coherence_delta_mean": x, "symptom_delta_mean": y, "rv_potency_delta_mean": z}}
    """
    if isinstance(repo, Neo4jMPGRepository):
        with repo.driver.session(database=repo.database) as session:
            for mid, scores in module_scores.items():
                session.run(
                    """
                    MATCH (:ProtocolInstance {id: $pid})-[:HAS_MODULE_STATE]->(ms:ModuleState {module_id: $mid})
                    SET ms.coherence_delta_mean = coalesce($coh, ms.coherence_delta_mean),
                        ms.symptom_delta_mean = coalesce($sym, ms.symptom_delta_mean),
                        ms.rv_potency_delta_mean = coalesce($rv, ms.rv_potency_delta_mean),
                        ms.last_review_time = datetime()
                    """,
                    pid=protocol_instance_id,
                    mid=mid,
                    coh=scores.get("coherence_delta_mean"),
                    sym=scores.get("symptom_delta_mean"),
                    rv=scores.get("rv_potency_delta_mean"),
                )
    else:
        for node_id, node in repo.nodes.items():  # type: ignore[union-attr]
            if isinstance(node, ModuleState) and node.protocol_instance_id == protocol_instance_id:
                if node.module_id in module_scores:
                    scores = module_scores[node.module_id]
                    node.coherence_delta_mean = scores.get("coherence_delta_mean", node.coherence_delta_mean)
                    node.symptom_delta_mean = scores.get("symptom_delta_mean", node.symptom_delta_mean)
                    node.rv_potency_delta_mean = scores.get("rv_potency_delta_mean", node.rv_potency_delta_mean)
                    node.last_review_time = time.time()
                    repo.nodes[node_id] = node  # type: ignore[index]


def update_step_state_scores(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    step_scores: Dict[str, Dict[str, float]],
) -> None:
    """
    step_scores: {step_state_id: {"last_outcome_score": x, "coherence_effect": y, "rv_effect": z, "user_burden_score": b}}
    """
    if isinstance(repo, Neo4jMPGRepository):
        with repo.driver.session(database=repo.database) as session:
            for ssid, scores in step_scores.items():
                session.run(
                    """
                    MATCH (ss:StepState {id: $id})
                    SET ss.last_outcome_score = coalesce($score, ss.last_outcome_score),
                        ss.coherence_effect = coalesce($coh, ss.coherence_effect),
                        ss.rv_effect = coalesce($rv, ss.rv_effect),
                        ss.user_burden_score = coalesce($burden, ss.user_burden_score)
                    """,
                    id=ssid,
                    score=scores.get("last_outcome_score"),
                    coh=scores.get("coherence_effect"),
                    rv=scores.get("rv_effect"),
                    burden=scores.get("user_burden_score"),
                )
    else:
        for node_id, node in repo.nodes.items():  # type: ignore[union-attr]
            if isinstance(node, StepState) and node_id in step_scores:
                scores = step_scores[node_id]
                node.last_outcome_score = scores.get("last_outcome_score", node.last_outcome_score)
                node.coherence_effect = scores.get("coherence_effect", node.coherence_effect)
                node.rv_effect = scores.get("rv_effect", node.rv_effect)
                node.user_burden_score = scores.get("user_burden_score", node.user_burden_score)
                repo.nodes[node_id] = node  # type: ignore[index]
