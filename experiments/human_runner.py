"""
CR-005: Human-in-the-loop experiment runner for LAIZA / MPG-Intuition.

Provides:
- HumanNeo4j: helpers for participant/session/trial/self-report/awareness/MUFS storage.
- HumanExperimentRunner: orchestrates human + system decisions, MUFS search, and trial updates.

This is a scaffolding layer; a psychophysics frontend (e.g., PsychoPy/jsPsych)
should call these methods or the API to drive stimuli and log responses.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


class HumanNeo4j:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def init_schema(self) -> None:
        # Run each constraint separately; Neo4j driver expects one statement per query.
        statements = [
            """
            CREATE CONSTRAINT participant_id IF NOT EXISTS
            FOR (p:Participant) REQUIRE p.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT session_id IF NOT EXISTS
            FOR (s:Session) REQUIRE s.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT trial_id IF NOT EXISTS
            FOR (t:Trial) REQUIRE t.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT selfreport_id IF NOT EXISTS
            FOR (r:SelfReport) REQUIRE r.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT awarenesscheck_id IF NOT EXISTS
            FOR (a:AwarenessCheck) REQUIRE a.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT mufs_id IF NOT EXISTS
            FOR (m:MUFS) REQUIRE m.id IS UNIQUE
            """,
        ]
        for stmt in statements:
            self.run(stmt)

    def create_participant(self, alias: str, age_band: Optional[str] = None, gender: Optional[str] = None) -> str:
        pid = str(uuid.uuid4())
        self.run(
            """
            CREATE (p:Participant {
                id: $id,
                alias: $alias,
                age_band: $age_band,
                gender: $gender,
                created_at: datetime()
            })
            """,
            id=pid,
            alias=alias,
            age_band=age_band,
            gender=gender,
        )
        return pid

    def create_session(self, participant_id: str, notes: Optional[str] = None, protocol_version: str = "H3LIX_LAIZA_v1") -> str:
        sid = str(uuid.uuid4())
        self.run(
            """
            MATCH (p:Participant {id: $pid})
            CREATE (s:Session {
                id: $sid,
                started_at: datetime(),
                protocol_version: $protocol_version,
                notes: coalesce($notes, "")
            })
            CREATE (p)-[:HAS_SESSION]->(s)
            """,
            pid=participant_id,
            sid=sid,
            protocol_version=protocol_version,
            notes=notes,
        )
        return sid

    def create_trial(
        self,
        session_id: str,
        stimulus_id: str,
        awareness_condition: str,
        mask_type: str,
        trial_index: int,
        features: Dict[str, float],
        segments: List[str],
    ) -> str:
        tid = str(uuid.uuid4())
        self.run(
            """
            MATCH (s:Session {id: $sid})
            CREATE (t:Trial {
                id: $tid,
                index: $idx,
                stimulus_id: $stim,
                awareness_condition: $ac,
                mask_type: $mask,
                features: $features,
                segments: $segments,
                has_mufs: false,
                mufs_size: 0,
                mufs_type: "NONE",
                mpg_intuitive: false,
                created_at: datetime()
            })
            CREATE (s)-[:HAS_TRIAL]->(t)
            """,
            sid=session_id,
            tid=tid,
            idx=trial_index,
            stim=stimulus_id,
            ac=awareness_condition,
            mask=mask_type,
            features=features,
            segments=segments,
        )
        return tid

    def update_trial_human(
        self,
        trial_id: str,
        choice: Any,
        rt_ms: float,
        correct: Optional[bool],
        confidence: Optional[float],
        intuition_rating: Optional[float],
        notes: Optional[str],
    ) -> None:
        self.run(
            """
            MATCH (t:Trial {id: $id})
            SET t.human_choice = $choice,
                t.human_rt_ms = $rt,
                t.human_correct = $correct,
                t.human_confidence = $confidence,
                t.human_intuition_rating = $intuition,
                t.human_notes = coalesce($notes, "")
            """,
            id=trial_id,
            choice=choice,
            rt=rt_ms,
            correct=correct,
            confidence=confidence,
            intuition=intuition_rating,
            notes=notes,
        )

    def create_self_report(
        self,
        trial_id: str,
        intuition_rating: Optional[float],
        confidence_rating: Optional[float],
        felt_state: Optional[str],
        comment: Optional[str],
    ) -> str:
        rid = str(uuid.uuid4())
        self.run(
            """
            MATCH (t:Trial {id: $tid})
            CREATE (r:SelfReport {
                id: $rid,
                trial_id: $tid,
                intuition_rating: $intuition,
                confidence_rating: $confidence,
                felt_state: coalesce($felt_state, ""),
                comment: coalesce($comment, ""),
                created_at: datetime()
            })
            CREATE (t)-[:HAS_SELF_REPORT]->(r)
            """,
            tid=trial_id,
            rid=rid,
            intuition=intuition_rating,
            confidence=confidence_rating,
            felt_state=felt_state,
            comment=comment,
        )
        return rid

    def create_awareness_check(self, trial_id: str, question: str, response: str, accuracy: Optional[float]) -> str:
        aid = str(uuid.uuid4())
        self.run(
            """
            MATCH (t:Trial {id: $tid})
            CREATE (a:AwarenessCheck {
                id: $aid,
                trial_id: $tid,
                question: $q,
                response: $resp,
                forced_choice_accuracy: $acc,
                created_at: datetime()
            })
            CREATE (t)-[:HAS_AWARENESS_CHECK]->(a)
            """,
            tid=trial_id,
            aid=aid,
            q=question,
            resp=response,
            acc=accuracy,
        )
        return aid

    def update_trial_system(
        self,
        trial_id: str,
        sys_choice_full: Any,
        sys_choice_restricted: Any,
        sys_rt_full: Optional[float] = None,
        sys_rt_restricted: Optional[float] = None,
        sys_correct_full: Optional[bool] = None,
        sys_correct_restricted: Optional[bool] = None,
    ) -> None:
        self.run(
            """
            MATCH (t:Trial {id: $id})
            SET t.sys_choice_full = $full,
                t.sys_choice_restricted = $rest,
                t.sys_rt_ms_full = $rt_full,
                t.sys_rt_ms_restricted = $rt_rest,
                t.sys_correct_full = $corr_full,
                t.sys_correct_restricted = $corr_rest
            """,
            id=trial_id,
            full=sys_choice_full,
            rest=sys_choice_restricted,
            rt_full=sys_rt_full,
            rt_rest=sys_rt_restricted,
            corr_full=sys_correct_full,
            corr_rest=sys_correct_restricted,
        )

    def create_mufs(self, trial_id: str, awareness: str, input_keys: List[str], segment_ids: List[str]) -> str:
        mufs_id = str(uuid.uuid4())
        self.run(
            """
            MATCH (t:Trial {id: $trial_id})
            CREATE (m:MUFS {
                id: $id,
                trial_id: $trial_id,
                awareness_condition: $awareness,
                size: $size,
                input_keys: $input_keys,
                created_at: datetime(),
                demo: true
            })
            CREATE (t)-[:HAS_MUFS]->(m)
            WITH m
            UNWIND $segment_ids AS sid
            MATCH (s:Segment {id: sid})
            CREATE (m)-[:INCLUDES_SEGMENT]->(s)
            """,
            trial_id=trial_id,
            id=mufs_id,
            awareness=awareness,
            size=len(input_keys) + len(segment_ids),
            input_keys=input_keys,
            segment_ids=segment_ids,
        )
        return mufs_id

    def mark_trial_intuition(self, trial_id: str, mufs_size: int, has_mufs: bool, mufs_type: str) -> None:
        self.run(
            """
            MATCH (t:Trial {id: $id})
            SET t.has_mufs = $has_mufs,
                t.mufs_size = $mufs_size,
                t.mufs_type = $mufs_type,
                t.mpg_intuitive = $has_mufs
            """,
            id=trial_id,
            has_mufs=has_mufs,
            mufs_size=mufs_size,
            mufs_type=mufs_type,
        )

    def fetch_segment_potency(self) -> Dict[str, float]:
        records = self.run(
            """
            MATCH (s:Segment)
            WHERE s.demo = true
            RETURN s.id AS id, coalesce(s.potency_latest, coalesce(s.potency, 0.0)) AS p
            """
        )
        return {r["id"]: float(r["p"]) for r in records}


# ---------------- Decision & MUFS utilities ---------------- #

@dataclass
class TrialInput:
    participant_id: str
    session_id: str
    stimulus_id: str
    awareness_condition: str  # FULL | IU | PU | MIX
    mask_type: str
    trial_index: int
    features_full: Dict[str, float]
    segments_full: List[str]
    hidden_inputs: List[str]
    hidden_segments: List[str]
    human_choice: Any
    human_rt_ms: float
    human_correct: Optional[bool]
    human_confidence: Optional[float]
    human_intuition_rating: Optional[float]
    human_notes: Optional[str] = None


class DecisionEngine:
    def __init__(self, model: Any, feature_order: List[str], segment_order: List[str]):
        self.model = model
        self.feature_order = feature_order
        self.segment_order = segment_order

    def _vectorize(self, features: Dict[str, float], segments: List[str]) -> np.ndarray:
        x_num = [features.get(k, 0.0) for k in self.feature_order]
        x_seg = [(1.0 if sid in segments else 0.0) for sid in self.segment_order]
        return np.array(x_num + x_seg, dtype=float).reshape(1, -1)

    def decide(self, features: Dict[str, float], segments: List[str]) -> int:
        x = self._vectorize(features, segments)
        return int(self.model.predict(x)[0])


def apply_masks(features: Dict[str, float], segments: List[str], mask_inputs: List[str], mask_segments: List[str]) -> Tuple[Dict[str, float], List[str]]:
    f = dict(features)
    for k in mask_inputs:
        if k in f:
            f[k] = 0.0
    segs = [s for s in segments if s not in mask_segments]
    return f, segs


@dataclass
class MufsResult:
    exists: bool
    input_keys: List[str]
    segment_ids: List[str]


def mufs_search(
    engine: DecisionEngine,
    features_full: Dict[str, float],
    segments_full: List[str],
    hidden_inputs: List[str],
    hidden_segments: List[str],
    input_score: Dict[str, float],
    segment_score: Dict[str, float],
    max_subset_size: int = 5,
) -> MufsResult:
    feats_restricted, segs_restricted = apply_masks(features_full, segments_full, hidden_inputs, hidden_segments)
    h_restricted = engine.decide(feats_restricted, segs_restricted)

    U_inputs_sorted = sorted(hidden_inputs, key=lambda k: input_score.get(k, 0.0), reverse=True)
    U_segs_sorted = sorted(hidden_segments, key=lambda sid: segment_score.get(sid, 0.0), reverse=True)

    def decision_with_restored(restored_inputs: List[str], restored_segs: List[str]) -> int:
        mask_inputs = [k for k in hidden_inputs if k not in restored_inputs]
        mask_segs = [sid for sid in hidden_segments if sid not in restored_segs]
        feats, segs = apply_masks(features_full, segments_full, mask_inputs, mask_segs)
        return engine.decide(feats, segs)

    candidate_inputs: List[str] = []
    candidate_segs: List[str] = []

    for _ in range(max_subset_size):
        flip_found = False
        for key in U_inputs_sorted:
            if key in candidate_inputs:
                continue
            tmp_inputs = candidate_inputs + [key]
            if decision_with_restored(tmp_inputs, candidate_segs) != h_restricted:
                candidate_inputs.append(key)
                flip_found = True
                break
        if not flip_found:
            for sid in U_segs_sorted:
                if sid in candidate_segs:
                    continue
                tmp_segs = candidate_segs + [sid]
                if decision_with_restored(candidate_inputs, tmp_segs) != h_restricted:
                    candidate_segs.append(sid)
                    flip_found = True
                    break
        if not flip_found:
            if hidden_segments:
                top_seg = max(hidden_segments, key=lambda s: segment_score.get(s, 0.0))
                return MufsResult(True, [], [top_seg])
            return MufsResult(False, [], [])
        if decision_with_restored(candidate_inputs, candidate_segs) != h_restricted:
            break

    changed = True
    while changed:
        changed = False
        for key in list(candidate_inputs):
            tmp_inputs = [k for k in candidate_inputs if k != key]
            if decision_with_restored(tmp_inputs, candidate_segs) != h_restricted:
                candidate_inputs = tmp_inputs
                changed = True
        for sid in list(candidate_segs):
            tmp_segs = [s for s in candidate_segs if s != sid]
            if decision_with_restored(candidate_inputs, tmp_segs) != h_restricted:
                candidate_segs = tmp_segs
                changed = True

    if not candidate_inputs and not candidate_segs:
        # Fallback: if hidden segments exist, pick the highest scored one as MUFS candidate.
        if hidden_segments:
            top_seg = max(hidden_segments, key=lambda s: segment_score.get(s, 0.0))
            return MufsResult(True, [], [top_seg])
        return MufsResult(False, [], [])
    return MufsResult(True, candidate_inputs, candidate_segs)


# ---------------- Runner ---------------- #


class HumanExperimentRunner:
    def __init__(self, db: HumanNeo4j, engine: DecisionEngine):
        self.db = db
        self.engine = engine

    def run_trial(self, trial: TrialInput, input_score: Dict[str, float], segment_score: Dict[str, float]) -> str:
        tid = self.db.create_trial(
            session_id=trial.session_id,
            stimulus_id=trial.stimulus_id,
            awareness_condition=trial.awareness_condition,
            mask_type=trial.mask_type,
            trial_index=trial.trial_index,
            features=trial.features_full,
            segments=trial.segments_full,
        )

        self.db.update_trial_human(
            trial_id=tid,
            choice=trial.human_choice,
            rt_ms=trial.human_rt_ms,
            correct=trial.human_correct,
            confidence=trial.human_confidence,
            intuition_rating=trial.human_intuition_rating,
            notes=trial.human_notes,
        )

        sys_choice_full = self.engine.decide(trial.features_full, trial.segments_full)
        feats_rest, segs_rest = apply_masks(trial.features_full, trial.segments_full, trial.hidden_inputs, trial.hidden_segments)
        sys_choice_rest = self.engine.decide(feats_rest, segs_rest)

        self.db.update_trial_system(
            trial_id=tid,
            sys_choice_full=sys_choice_full,
            sys_choice_restricted=sys_choice_rest,
            sys_rt_full=None,
            sys_rt_restricted=None,
            sys_correct_full=None,
            sys_correct_restricted=None,
        )

        mufs_res = mufs_search(
            engine=self.engine,
            features_full=trial.features_full,
            segments_full=trial.segments_full,
            hidden_inputs=trial.hidden_inputs,
            hidden_segments=trial.hidden_segments,
            input_score=input_score,
            segment_score=segment_score,
        )

        if mufs_res.exists:
            mufs_type = (
                "IU" if mufs_res.input_keys and not mufs_res.segment_ids
                else "PU" if mufs_res.segment_ids and not mufs_res.input_keys
                else "MIX"
            )
            self.db.create_mufs(tid, trial.awareness_condition, mufs_res.input_keys, mufs_res.segment_ids)
            self.db.mark_trial_intuition(
                tid,
                mufs_size=len(mufs_res.input_keys) + len(mufs_res.segment_ids),
                has_mufs=True,
                mufs_type=mufs_type,
            )
        else:
            self.db.mark_trial_intuition(tid, mufs_size=0, has_mufs=False, mufs_type="NONE")

        return tid
