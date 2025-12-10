"""
Load clinical protocol templates (CR-107) into Neo4j.
"""

from __future__ import annotations

import uuid

from mpg.protocols import (
    OutcomeMeasure,
    ProtocolModule,
    ProtocolStep,
    ProtocolTemplate,
    load_protocol_template,
)
from mpg.repository import Neo4jMPGRepository


def social_anxiety() -> tuple[ProtocolTemplate, list[ProtocolModule], list[ProtocolStep], list[OutcomeMeasure]]:
    pid = str(uuid.uuid4())
    modules = [
        ProtocolModule(
            id=str(uuid.uuid4()),
            protocol_id=pid,
            name="Psychoeducation & mapping",
            order_index=1,
            description="SORK map for social situations; link somatic cues.",
            goal_summary="Shared case map and awareness of somatic cues.",
            duration_sessions_estimate=1,
        ),
        ProtocolModule(
            id=str(uuid.uuid4()),
            protocol_id=pid,
            name="Monitoring & belief tracking",
            order_index=2,
            description="Track social interactions, predictions vs outcomes, intuition.",
            goal_summary="Calibrate predictions; gather somatic/context data.",
            duration_sessions_estimate=2,
        ),
        ProtocolModule(
            id=str(uuid.uuid4()),
            protocol_id=pid,
            name="Exposure & behavioral experiments",
            order_index=3,
            description="Graded exposures; decision tasks with feedback.",
            goal_summary="Reduce avoidance; improve calibration.",
            duration_sessions_estimate=3,
        ),
    ]
    steps = [
        ProtocolStep(
            id=str(uuid.uuid4()),
            module_id=modules[0].id,
            name="SORK map for social triggers",
            step_type="IN_SESSION_EXERCISE",
            suggested_repetitions=1,
        ),
        ProtocolStep(
            id=str(uuid.uuid4()),
            module_id=modules[1].id,
            name="Daily social check-in",
            step_type="HOMEWORK_TASK",
            kmp_task_template_id="social_checkin",
            suggested_repetitions=14,
        ),
        ProtocolStep(
            id=str(uuid.uuid4()),
            module_id=modules[2].id,
            name="Exposure decision task",
            step_type="HOMEWORK_TASK",
            kmp_task_template_id="social_exposure_task",
            suggested_repetitions=6,
        ),
    ]
    outcomes = [
        OutcomeMeasure(
            id=str(uuid.uuid4()),
            name="Social anxiety rating",
            domain="SYMPTOM",
            scale_type="LIKERT",
            collection_mode="SELF_REPORT",
            target_frequency="WEEKLY",
        ),
        OutcomeMeasure(
            id=str(uuid.uuid4()),
            name="Coherence during exposures",
            domain="COHERENCE",
            scale_type="CONTINUOUS",
            collection_mode="PASSIVE_STREAM",
            target_frequency="EACH_SESSION",
        ),
    ]
    template = ProtocolTemplate(
        id=pid,
        name="Social Anxiety / Performance",
        target_condition="SOCIAL_ANXIETY",
        description="Brief exposure-focused protocol with SORK mapping and monitoring.",
        sorkn_focus={
            "S": ["presentations", "meetings", "social evaluation"],
            "O": ["fear of humiliation", "mental imagery", "HRV changes"],
            "R": ["avoidance", "safety behaviors", "rumination"],
            "K": ["short-term relief", "long-term isolation"],
            "N": ["coherence during exposure", "RV potency reduction"],
        },
        risk_tier="LOW",
        status="TEMPLATE",
    )
    return template, modules, steps, outcomes


def insomnia() -> tuple[ProtocolTemplate, list[ProtocolModule], list[ProtocolStep], list[OutcomeMeasure]]:
    pid = str(uuid.uuid4())
    modules = [
        ProtocolModule(
            id=str(uuid.uuid4()),
            protocol_id=pid,
            name="Sleep profiling",
            order_index=1,
            description="Monitor sleep and somatic markers.",
            goal_summary="Baseline sleep + somatic profile.",
            duration_sessions_estimate=1,
        ),
        ProtocolModule(
            id=str(uuid.uuid4()),
            protocol_id=pid,
            name="Behavioral restructuring",
            order_index=2,
            description="Sleep schedule, hygiene, reduce safety behaviors.",
            goal_summary="Stabilize schedule and habits.",
            duration_sessions_estimate=2,
        ),
    ]
    steps = [
        ProtocolStep(
            id=str(uuid.uuid4()),
            module_id=modules[0].id,
            name="Nightly sleep log",
            step_type="HOMEWORK_TASK",
            kmp_task_template_id="sleep_log",
            suggested_repetitions=14,
        ),
        ProtocolStep(
            id=str(uuid.uuid4()),
            module_id=modules[1].id,
            name="Sleep hygiene checklist",
            step_type="HOMEWORK_TASK",
            kmp_task_template_id="sleep_hygiene",
            suggested_repetitions=14,
        ),
    ]
    outcomes = [
        OutcomeMeasure(
            id=str(uuid.uuid4()),
            name="Sleep onset latency",
            domain="FUNCTION",
            scale_type="CONTINUOUS",
            collection_mode="PASSIVE_STREAM",
            target_frequency="EACH_SESSION",
        ),
        OutcomeMeasure(
            id=str(uuid.uuid4()),
            name="Nighttime HRV",
            domain="COHERENCE",
            scale_type="CONTINUOUS",
            collection_mode="PASSIVE_STREAM",
            target_frequency="EACH_SESSION",
        ),
    ]
    template = ProtocolTemplate(
        id=pid,
        name="Insomnia / Sleep Dysregulation",
        target_condition="INSOMNIA",
        description="Short behavioral protocol for sleep stabilization.",
        sorkn_focus={
            "S": ["bedtime", "screens", "late stressors"],
            "O": ["catastrophic sleep beliefs", "hyperarousal"],
            "R": ["naps", "screen time", "sleep procrastination"],
            "K": ["fatigue", "cognitive fog"],
            "N": ["sleep coherence", "potency of sleep catastrophe segment"],
        },
        risk_tier="LOW",
        status="TEMPLATE",
    )
    return template, modules, steps, outcomes


def decision_fatigue() -> tuple[ProtocolTemplate, list[ProtocolModule], list[ProtocolStep], list[OutcomeMeasure]]:
    pid = str(uuid.uuid4())
    modules = [
        ProtocolModule(
            id=str(uuid.uuid4()),
            protocol_id=pid,
            name="Decision tracing",
            order_index=1,
            description="Log daily decisions with confidence and somatic context.",
            goal_summary="Baseline calibration and load.",
            duration_sessions_estimate=1,
        ),
        ProtocolModule(
            id=str(uuid.uuid4()),
            protocol_id=pid,
            name="Calibration exercises",
            order_index=2,
            description="Structured decision tasks with feedback.",
            goal_summary="Improve calibration and timing.",
            duration_sessions_estimate=2,
        ),
    ]
    steps = [
        ProtocolStep(
            id=str(uuid.uuid4()),
            module_id=modules[0].id,
            name="Decision diary",
            step_type="HOMEWORK_TASK",
            kmp_task_template_id="decision_diary",
            suggested_repetitions=14,
        ),
        ProtocolStep(
            id=str(uuid.uuid4()),
            module_id=modules[1].id,
            name="Calibration task",
            step_type="HOMEWORK_TASK",
            kmp_task_template_id="calibration_task",
            suggested_repetitions=6,
        ),
    ]
    outcomes = [
        OutcomeMeasure(
            id=str(uuid.uuid4()),
            name="Decision coherence",
            domain="COHERENCE",
            scale_type="CONTINUOUS",
            collection_mode="PASSIVE_STREAM",
            target_frequency="EACH_SESSION",
        ),
        OutcomeMeasure(
            id=str(uuid.uuid4()),
            name="Commitment errors",
            domain="FUNCTION",
            scale_type="CONTINUOUS",
            collection_mode="SELF_REPORT",
            target_frequency="WEEKLY",
        ),
    ]
    template = ProtocolTemplate(
        id=pid,
        name="Decision Fatigue / Overcommitment",
        target_condition="DECISION_FATIGUE",
        description="Decision calibration and commitment hygiene protocol.",
        sorkn_focus={
            "S": ["high decision load", "notifications", "conflicts"],
            "O": ["obligation beliefs", "FOMO", "fear of missing out"],
            "R": ["over-commit", "procrastinate"],
            "K": ["burnout", "errors"],
            "N": ["coherence-aware timing", "RV potency reduction"],
        },
        risk_tier="LOW",
        status="TEMPLATE",
    )
    return template, modules, steps, outcomes


def main() -> None:
    repo = Neo4jMPGRepository(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "neo4j-password"),
    )
    templates = [social_anxiety(), insomnia(), decision_fatigue()]
    for tpl in templates:
        template, modules, steps, outcomes = tpl
        load_protocol_template(repo, template, modules, steps, outcomes)
    repo.close()


if __name__ == "__main__":
    import os

    main()
