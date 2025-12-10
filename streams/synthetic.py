from __future__ import annotations

import asyncio
import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence

from schemas.telemetry import (
    DecisionUtility,
    MessageType,
    MpgDeltaPayload,
    MpgEdge,
    MpgNode,
    MpgNodeMetrics,
    MpgOperation,
    MpgSegment,
    MufsEventPayload,
    NoeticIntuitiveAccuracyEstimate,
    NoeticSpectrumBand,
    NoeticStatePayload,
    NoeticStreamCorrelation,
    RogueVariableEventPayload,
    RogueVariableImpactFactors,
    RogueVariableShapleyStats,
    SomaticAnticipatoryMarker,
    SomaticStatePayload,
    SourceLayer,
    StreamName,
    SymbolicBelief,
    SymbolicPrediction,
    SymbolicPredictionOption,
    SymbolicUncertaintyRegion,
    SymbolicStatePayload,
    TelemetryEnvelope,
    UnawarenessType,
)
from streams.bus import StreamBus


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


@dataclass
class ScenarioConfig:
    name: str
    duration_s: float = 30.0
    interval_ms: int = 500
    include_graph_deltas: bool = True


class SyntheticTelemetryGenerator:
    """Scenario-based telemetry sandbox used for Vision Pro demos (SYNT.md)."""

    def __init__(self, bus: StreamBus, max_log: int = 20000):
        self.bus = bus
        self.max_log = max_log
        self._tasks: Dict[str, asyncio.Task] = {}
        self._logs: Dict[str, List[TelemetryEnvelope]] = defaultdict(list)
        self._scenarios: Dict[str, ScenarioConfig] = {
            "calm_baseline": ScenarioConfig("calm_baseline"),
            "rising_stress": ScenarioConfig("rising_stress"),
            "sudden_anomaly": ScenarioConfig("sudden_anomaly"),
            "high_coherence_insight": ScenarioConfig("high_coherence_insight"),
            "rogue_variable_storm": ScenarioConfig("rogue_variable_storm"),
            "mufs_flip_decision": ScenarioConfig("mufs_flip_decision"),
        }

    def available_scenarios(self) -> Sequence[str]:
        return list(self._scenarios.keys())

    def scenario_config(self, name: str) -> ScenarioConfig:
        if name not in self._scenarios:
            raise ValueError(f"Unknown scenario '{name}'. Options: {', '.join(self.available_scenarios())}")
        return self._scenarios[name]

    def get_log(self, session_id: str) -> List[TelemetryEnvelope]:
        return list(self._logs.get(session_id, []))

    def clear_log(self, session_id: str) -> None:
        self._logs.pop(session_id, None)

    def stop(self, session_id: str) -> bool:
        task = self._tasks.pop(session_id, None)
        if task:
            task.cancel()
            return True
        return False

    async def start(
        self,
        scenario: str,
        session_id: str,
        participant_id: str = "demo-user",
        duration_s: Optional[float] = None,
        interval_ms: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> str:
        config = self.scenario_config(scenario)
        duration = float(duration_s or config.duration_s)
        interval = int(interval_ms or config.interval_ms)
        if interval <= 0:
            raise ValueError("interval_ms must be positive")

        self.stop(session_id)
        self.clear_log(session_id)

        run_id = str(uuid.uuid4())
        rng = random.Random(seed or int(datetime.now(tz=timezone.utc).timestamp() * 1000))
        total_steps = max(1, int(math.ceil((duration * 1000.0) / interval)))
        start_ts = datetime.now(tz=timezone.utc)

        async def _runner() -> None:
            seq = 0
            state: Dict[str, float] = {
                "hr": 68.0 + rng.uniform(-2.0, 2.0),
                "hrv": 70.0 + rng.uniform(-10.0, 10.0),
                "eda": 0.22 + rng.uniform(-0.04, 0.04),
                "coherence": 0.65 + rng.uniform(-0.05, 0.05),
            }
            try:
                for step in range(total_steps):
                    progress = step / max(total_steps - 1, 1)
                    t_rel_ms = step * interval
                    ts = start_ts + timedelta(milliseconds=t_rel_ms)
                    envelopes = self._build_tick(
                        scenario=scenario,
                        state=state,
                        rng=rng,
                        session_id=session_id,
                        participant_id=participant_id,
                        run_id=run_id,
                        progress=progress,
                        timestamp=ts,
                        t_rel_ms=t_rel_ms,
                    )
                    for env in envelopes:
                        env.sequence = seq
                        seq += 1
                        await self._publish(env)
                    await asyncio.sleep(interval / 1000.0)
            except asyncio.CancelledError:
                return
            finally:
                self._tasks.pop(session_id, None)

        self._tasks[session_id] = asyncio.create_task(_runner())
        return run_id

    async def _publish(self, envelope: TelemetryEnvelope) -> None:
        log = self._logs[envelope.session_id]
        log.append(envelope)
        if len(log) > self.max_log:
            self._logs[envelope.session_id] = log[-self.max_log :]
        meta = {
            "session_id": envelope.session_id,
            "participant_id": envelope.subject_id,
            "message_type": envelope.message_type.value,
            "aligned_ts_ms": int(envelope.timestamp_utc.timestamp() * 1000.0),
            "run_id": envelope.run_id,
        }
        await self.bus.publish({"kind": "telemetry", "telemetry": envelope.model_dump(mode="json"), "meta": meta})

    def _build_tick(
        self,
        scenario: str,
        state: Dict[str, float],
        rng: random.Random,
        session_id: str,
        participant_id: str,
        run_id: str,
        progress: float,
        timestamp: datetime,
        t_rel_ms: int,
    ) -> List[TelemetryEnvelope]:
        envelopes: List[TelemetryEnvelope] = []

        somatic = self._somatic_payload(scenario, state, rng, t_rel_ms)
        envelopes.append(
            TelemetryEnvelope(
                message_type=MessageType.SOMATIC_STATE,
                timestamp_utc=timestamp,
                experiment_id=scenario,
                session_id=session_id,
                subject_id=participant_id,
                run_id=run_id,
                source_layer=SourceLayer.SOMATIC,
                sequence=0,
                payload=somatic,
            )
        )

        symbolic = self._symbolic_payload(scenario, state, rng, t_rel_ms)
        envelopes.append(
            TelemetryEnvelope(
                message_type=MessageType.SYMBOLIC_STATE,
                timestamp_utc=timestamp,
                experiment_id=scenario,
                session_id=session_id,
                subject_id=participant_id,
                run_id=run_id,
                source_layer=SourceLayer.SYMBOLIC,
                sequence=0,
                payload=symbolic,
            )
        )

        noetic = self._noetic_payload(scenario, state, rng, t_rel_ms)
        envelopes.append(
            TelemetryEnvelope(
                message_type=MessageType.NOETIC_STATE,
                timestamp_utc=timestamp,
                experiment_id=scenario,
                session_id=session_id,
                subject_id=participant_id,
                run_id=run_id,
                source_layer=SourceLayer.NOETIC,
                sequence=0,
                payload=noetic,
            )
        )

        if scenario in {"rogue_variable_storm", "sudden_anomaly"} and rng.random() < 0.25 + 0.35 * progress:
            envelopes.append(self._rogue_event(session_id, participant_id, run_id, timestamp))

        if scenario in {"mufs_flip_decision", "high_coherence_insight"} and progress > 0.65 and rng.random() < 0.35:
            envelopes.append(self._mufs_event(session_id, participant_id, run_id, timestamp))

        if scenario in {"rogue_variable_storm", "rising_stress"} and rng.random() < 0.20 + 0.3 * progress:
            envelopes.append(self._mpg_delta(session_id, participant_id, run_id, timestamp, rng))

        return envelopes

    def _somatic_payload(
        self, scenario: str, state: Dict[str, float], rng: random.Random, t_rel_ms: int
    ) -> SomaticStatePayload:
        hr = state.get("hr", 70.0)
        hrv = state.get("hrv", 70.0)
        eda = state.get("eda", 0.22)

        if scenario == "rising_stress":
            hr += rng.uniform(0.5, 1.4)
            hrv -= rng.uniform(0.8, 1.5)
            eda += rng.uniform(0.015, 0.035)
        elif scenario == "calm_baseline":
            hr += rng.uniform(-0.35, 0.35)
            hrv += rng.uniform(-0.5, 0.5)
            eda += rng.uniform(-0.01, 0.01)
        elif scenario == "sudden_anomaly":
            if rng.random() < 0.1:
                hr += rng.uniform(6.0, 12.0)
                hrv -= rng.uniform(8.0, 12.0)
                eda += rng.uniform(0.08, 0.16)
            else:
                hr += rng.uniform(-0.4, 0.4)
                hrv += rng.uniform(-1.0, 1.0)
                eda += rng.uniform(-0.01, 0.02)
        elif scenario == "high_coherence_insight":
            hr += rng.uniform(-0.25, 0.25)
            hrv += rng.uniform(0.6, 1.0)
            eda += rng.uniform(-0.01, 0.02)
        elif scenario == "rogue_variable_storm":
            hr += rng.uniform(1.0, 2.5)
            hrv -= rng.uniform(1.0, 2.0)
            eda += rng.uniform(0.03, 0.06)
        elif scenario == "mufs_flip_decision":
            hr += rng.uniform(0.5, 1.0)
            hrv -= rng.uniform(0.5, 1.0)
            eda += rng.uniform(0.02, 0.04)

        hr = max(52.0, min(140.0, hr))
        hrv = max(15.0, min(120.0, hrv))
        eda = _clamp(eda, 0.05, 2.0)

        state["hr"] = hr
        state["hrv"] = hrv
        state["eda"] = eda

        anticipatory: List[SomaticAnticipatoryMarker] = []
        change_point = False
        anomaly_score: Optional[float] = None
        if scenario in {"mufs_flip_decision", "high_coherence_insight"} and t_rel_ms > 18000:
            anticipatory.append(
                SomaticAnticipatoryMarker(marker_type="readiness_like", lead_time_ms=600, confidence=0.65 + rng.random() * 0.25)
            )
        if scenario == "sudden_anomaly" and eda > 0.35:
            change_point = True
            anomaly_score = _clamp(0.6 + rng.random() * 0.35)
        if scenario == "rogue_variable_storm" and eda > 0.4:
            change_point = True
            anomaly_score = _clamp(0.5 + rng.random() * 0.4)

        return SomaticStatePayload(
            t_rel_ms=t_rel_ms,
            window_ms=1000,
            features={
                "hr": round(hr, 2),
                "hrv_sdnn": round(hrv, 2),
                "eda": round(eda, 3),
                "respiration_rate": round(12.5 + rng.uniform(-0.4, 1.5), 2),
                "pupil_diameter": round(3.1 + rng.uniform(-0.3, 0.6), 2),
            },
            global_uncertainty_score=_clamp(0.2 + rng.random() * 0.3) if scenario != "high_coherence_insight" else _clamp(0.1 + rng.random() * 0.2),
            change_point=change_point,
            anomaly_score=anomaly_score,
            anticipatory_markers=anticipatory,
        )

    def _symbolic_payload(
        self, scenario: str, state: Dict[str, float], rng: random.Random, t_rel_ms: int
    ) -> SymbolicStatePayload:
        belief_revision_id = f"br_{t_rel_ms}"
        beliefs: List[SymbolicBelief] = []

        themes = [
            ("project_focus", 0.12),
            ("fatigue", -0.22),
            ("support", 0.18),
            ("deadline_risk", -0.28),
            ("intuition", 0.2),
            ("alignment", 0.15),
            ("rogue_hint", -0.05),
            ("coherence_glimmer", 0.25),
        ]
        conflict_boost = 0.12 if scenario in {"rogue_variable_storm", "rising_stress", "sudden_anomaly"} else 0.0
        for idx, (label, base_valence) in enumerate(themes):
            imp = _clamp(0.35 + rng.random() * 0.4 + conflict_boost * (1 if idx % 3 == 0 else 0))
            conf = _clamp(0.55 + rng.random() * 0.3 - (0.1 if scenario == "rising_stress" else 0.0))
            val = _clamp(base_valence + rng.uniform(-0.12, 0.12), -1.0, 1.0)
            beliefs.append(
                SymbolicBelief(
                    id=f"b{idx}",
                    kind="entity" if idx % 2 == 0 else "event",
                    label=label,
                    valence=val,
                    intensity=_clamp(0.35 + rng.random() * 0.4),
                    recency=_clamp(0.5 + rng.random() * 0.35),
                    stability=_clamp(0.4 + rng.random() * 0.3),
                    confidence=conf,
                    importance=imp,
                )
            )

        contradictory = SymbolicBelief(
            id="b_conflict",
            kind="relation",
            label="approach_vs_avoid",
            valence=-0.05 if scenario != "high_coherence_insight" else 0.15,
            intensity=_clamp(0.45 + conflict_boost + rng.random() * 0.25),
            recency=_clamp(0.45 + rng.random() * 0.2),
            stability=_clamp(0.25 + rng.random() * 0.25),
            confidence=_clamp(0.55 + conflict_boost + rng.random() * 0.2),
            importance=_clamp(0.5 + conflict_boost + rng.random() * 0.2),
        )
        beliefs.append(contradictory)

        predictions: List[SymbolicPrediction] = []
        predictions.append(
            SymbolicPrediction(
                id="p_outcome",
                target_type="outcome",
                horizon_ms=5000,
                topk=[
                    SymbolicPredictionOption(value="positive_outcome", probability=_clamp(0.55 if scenario == "high_coherence_insight" else 0.35 + rng.random() * 0.2)),
                    SymbolicPredictionOption(value="negative_outcome", probability=_clamp(0.45 if scenario != "high_coherence_insight" else 0.25 + rng.random() * 0.15)),
                ],
            )
        )

        uncertainty_regions: List[SymbolicUncertaintyRegion] = []
        if conflict_boost > 0.0:
            uncertainty_regions.append(
                SymbolicUncertaintyRegion(
                    label="conflict_hotspot",
                    belief_ids=["b_conflict", "b1", "b3"],
                    comment="Competing beliefs raise risk",
                )
            )

        return SymbolicStatePayload(
            t_rel_ms=t_rel_ms,
            belief_revision_id=belief_revision_id,
            beliefs=beliefs,
            predictions=predictions,
            uncertainty_regions=uncertainty_regions,
        )

    def _noetic_payload(
        self, scenario: str, state: Dict[str, float], rng: random.Random, t_rel_ms: int
    ) -> NoeticStatePayload:
        base_coherence = state.get("coherence", 0.65)
        drift = rng.uniform(-0.02, 0.02)
        if scenario == "rising_stress":
            base_coherence -= rng.uniform(0.01, 0.04)
        elif scenario == "calm_baseline":
            base_coherence += rng.uniform(-0.01, 0.02)
        elif scenario == "sudden_anomaly":
            base_coherence -= rng.uniform(0.0, 0.06)
        elif scenario == "high_coherence_insight":
            base_coherence += rng.uniform(0.03, 0.06)
        elif scenario == "rogue_variable_storm":
            base_coherence -= rng.uniform(0.02, 0.05)
        elif scenario == "mufs_flip_decision":
            base_coherence -= rng.uniform(0.0, 0.03)
        coherence = _clamp(base_coherence + drift)
        state["coherence"] = coherence

        entropy_change = rng.uniform(-0.05, 0.05)
        if scenario in {"rising_stress", "rogue_variable_storm", "sudden_anomaly"}:
            entropy_change += rng.uniform(0.05, 0.12)
        elif scenario == "high_coherence_insight":
            entropy_change -= rng.uniform(0.04, 0.08)

        corr = [
            NoeticStreamCorrelation(stream_x=StreamName.SOMATIC, stream_y=StreamName.SYMBOLIC, r=_clamp(0.35 + rng.uniform(-0.15, 0.2), -1.0, 1.0)),
            NoeticStreamCorrelation(stream_x=StreamName.SOMATIC, stream_y=StreamName.BEHAVIORAL, r=_clamp(0.28 + rng.uniform(-0.2, 0.18), -1.0, 1.0)),
            NoeticStreamCorrelation(stream_x=StreamName.SYMBOLIC, stream_y=StreamName.BEHAVIORAL, r=_clamp(0.4 + rng.uniform(-0.2, 0.2), -1.0, 1.0)),
        ]

        spectrum = [
            NoeticSpectrumBand(band_label="low", freq_range_hz=(0.0, 0.2), coherence_strength=_clamp(coherence - 0.15 + rng.uniform(-0.05, 0.05))),
            NoeticSpectrumBand(band_label="mid", freq_range_hz=(0.2, 0.45), coherence_strength=_clamp(coherence + rng.uniform(-0.05, 0.07))),
            NoeticSpectrumBand(band_label="high", freq_range_hz=(0.45, 0.8), coherence_strength=_clamp(coherence - 0.1 + rng.uniform(-0.05, 0.05))),
        ]

        insight_estimate = None
        if scenario in {"high_coherence_insight", "mufs_flip_decision"}:
            insight_estimate = NoeticIntuitiveAccuracyEstimate(
                p_better_than_baseline=_clamp(0.6 + rng.random() * 0.25),
                calibration_error=_clamp(rng.uniform(0.05, 0.15)),
            )

        return NoeticStatePayload(
            t_rel_ms=t_rel_ms,
            window_ms=1000,
            global_coherence_score=coherence,
            entropy_change=entropy_change,
            stream_correlations=corr,
            coherence_spectrum=spectrum,
            intuitive_accuracy_estimate=insight_estimate,
        )

    def _mpg_delta(
        self, session_id: str, participant_id: str, run_id: str, timestamp: datetime, rng: random.Random
    ) -> TelemetryEnvelope:
        node_id = f"n{uuid.uuid4().hex[:6]}"
        node = MpgNode(
            id=node_id,
            label=f"Stress driver {node_id[-3:]}",
            layer_tags=["Psychological", "Professional"] if rng.random() < 0.5 else ["Somatic"],
            metrics=MpgNodeMetrics(
                valence=_clamp(rng.uniform(-0.4, 0.1), -1.0, 1.0),
                intensity=_clamp(0.4 + rng.random() * 0.4),
                recency=_clamp(0.5 + rng.random() * 0.4),
                stability=_clamp(0.35 + rng.random() * 0.35),
            ),
            confidence=_clamp(0.45 + rng.random() * 0.3),
            importance=_clamp(0.45 + rng.random() * 0.35),
            roles=["Segment"],
        )
        seg = MpgSegment(
            id=f"s{uuid.uuid4().hex[:6]}",
            label="Emergent cluster",
            level=1,
            member_node_ids=[node.id],
            cohesion=_clamp(0.5 + rng.random() * 0.3),
            average_importance=node.importance,
            average_confidence=node.confidence,
            affective_load=node.metrics.intensity,
        )
        edge = MpgEdge(
            id=f"{node.id}->root",
            source=node.id,
            target="root",
            type="amplifies",
            strength=_clamp(0.4 + rng.random() * 0.4),
            confidence=_clamp(0.4 + rng.random() * 0.3),
        )
        ops = [
            MpgOperation(kind="add_node", node=node),
            MpgOperation(kind="add_segment", segment=seg),
            MpgOperation(kind="add_edge", edge=edge),
        ]
        payload = MpgDeltaPayload(mpg_id="mpg_demo", level=1, delta_id=str(uuid.uuid4()), operations=ops)
        return TelemetryEnvelope(
            message_type=MessageType.MPG_DELTA,
            timestamp_utc=timestamp,
            experiment_id="synthetic_mpg",
            session_id=session_id,
            subject_id=participant_id,
            run_id=run_id,
            source_layer=SourceLayer.MPG,
            sequence=0,
            payload=payload,
        )

    def _rogue_event(self, session_id: str, participant_id: str, run_id: str, timestamp: datetime) -> TelemetryEnvelope:
        shapley = RogueVariableShapleyStats(
            mean_abs_contrib=0.12,
            std_abs_contrib=0.04,
            candidate_abs_contrib=0.28,
            z_score=2.45,
        )
        impact = RogueVariableImpactFactors(
            rate_of_change=0.78,
            breadth_of_impact=0.62,
            amplification=0.71,
            emotional_load=0.66,
            gate_leverage=0.53,
            robustness=0.44,
        )
        payload = RogueVariableEventPayload(
            rogue_id=f"rv_{uuid.uuid4().hex[:6]}",
            mpg_id="mpg_demo",
            candidate_type="segment",
            level_range=(1, 2),
            segment_ids=["s_driver", "s_alignment"],
            shapley_stats=shapley,
            potency_index=0.74,
            impact_factors=impact,
        )
        return TelemetryEnvelope(
            message_type=MessageType.ROGUE_VARIABLE_EVENT,
            timestamp_utc=timestamp,
            experiment_id="synthetic_rv",
            session_id=session_id,
            subject_id=participant_id,
            run_id=run_id,
            source_layer=SourceLayer.MPG,
            sequence=0,
            payload=payload,
        )

    def _mufs_event(self, session_id: str, participant_id: str, run_id: str, timestamp: datetime) -> TelemetryEnvelope:
        decision_full = DecisionUtility(choice="accept_plan", utility={"reward": 0.62, "risk": 0.22})
        decision_without_u = DecisionUtility(choice="delay_plan", utility={"reward": 0.41, "risk": 0.12})
        payload = MufsEventPayload(
            mufs_id=f"mufs_{uuid.uuid4().hex[:6]}",
            decision_id=f"dec_{uuid.uuid4().hex[:5]}",
            mpg_id="mpg_demo",
            unawareness_types=[UnawarenessType.INPUT, UnawarenessType.PROCESS],
            input_unaware_refs=["missing_email_cue"],
            process_unaware_node_ids=["s_driver"],
            decision_full=decision_full,
            decision_without_U=decision_without_u,
            minimal=True,
            search_metadata={"method": "synthetic_bruteforce", "iterations": 12},
        )
        return TelemetryEnvelope(
            message_type=MessageType.MUFS_EVENT,
            timestamp_utc=timestamp,
            experiment_id="synthetic_mufs",
            session_id=session_id,
            subject_id=participant_id,
            run_id=run_id,
            source_layer=SourceLayer.MIRROR_CORE,
            sequence=0,
            payload=payload,
        )
