"""
CR-004: MUFS search & MPG-Intuition harness (system-only demo).

Simulates trials with full vs restricted awareness (IU/PU), runs a MUFS search
to find minimal subsets of hidden inputs/segments whose restoration flips
the decision, and writes MUFS + intuition flags to Neo4j.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

import numpy as np
from neo4j import GraphDatabase
from sklearn.ensemble import RandomForestClassifier

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


# ---------------- Neo4j Helpers ---------------- #

class LAIZANeo4j:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def init_mufs_schema(self) -> None:
        self.run(
            """
            CREATE CONSTRAINT mufs_id IF NOT EXISTS
            FOR (m:MUFS) REQUIRE m.id IS UNIQUE;
            """
        )
        self.run(
            """
            // Ensure trial defaults exist (idempotent set)
            MATCH (t:Trial)
            SET t.awareness_condition = coalesce(t.awareness_condition, "FULL"),
                t.mask_type = coalesce(t.mask_type, "NONE"),
                t.has_mufs = coalesce(t.has_mufs, false),
                t.mufs_size = coalesce(t.mufs_size, 0),
                t.mufs_type = coalesce(t.mufs_type, "NONE"),
                t.mpg_intuitive = coalesce(t.mpg_intuitive, false)
            """
        )

    def create_trial(self, awareness: str, features: Dict[str, float], segments: List[str]) -> str:
        tid = str(uuid.uuid4())
        self.run(
            """
            CREATE (t:Trial {
                id: $id,
                awareness_condition: $awareness,
                mask_type: $awareness,
                has_mufs: false,
                mufs_size: 0,
                mufs_type: "NONE",
                mpg_intuitive: false,
                demo: true,
                features: $features,
                segments: $segments
            })
            RETURN t
            """,
            id=tid,
            awareness=awareness,
            features=features,
            segments=segments,
        )
        return tid

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


# ---------------- Decision Engine ---------------- #

@dataclass
class TrialConfig:
    trial_id: str
    features_full: Dict[str, float]
    segments_full: List[str]
    hidden_inputs: List[str]
    hidden_segments: List[str]
    awareness: str


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


def apply_masks(cfg: TrialConfig, mask_inputs: List[str], mask_segments: List[str]) -> Tuple[Dict[str, float], List[str]]:
    features = dict(cfg.features_full)
    for key in mask_inputs:
        if key in features:
            features[key] = 0.0
    segments = [s for s in cfg.segments_full if s not in mask_segments]
    return features, segments


@dataclass
class MufsResult:
    exists: bool
    input_keys: List[str]
    segment_ids: List[str]


def mufs_search(
    engine: DecisionEngine,
    cfg: TrialConfig,
    input_score: Dict[str, float],
    segment_score: Dict[str, float],
    max_subset_size: int = 5,
) -> MufsResult:
    feats_restricted, segs_restricted = apply_masks(cfg, cfg.hidden_inputs, cfg.hidden_segments)
    h_restricted = engine.decide(feats_restricted, segs_restricted)

    U_inputs = list(cfg.hidden_inputs)
    U_segs = list(cfg.hidden_segments)
    U_inputs_sorted = sorted(U_inputs, key=lambda k: input_score.get(k, 0.0), reverse=True)
    U_segs_sorted = sorted(U_segs, key=lambda sid: segment_score.get(sid, 0.0), reverse=True)

    def decision_with_restored(restored_inputs: List[str], restored_segs: List[str]) -> int:
        mask_inputs = [k for k in U_inputs if k not in restored_inputs]
        mask_segs = [sid for sid in U_segs if sid not in restored_segs]
        feats, segs = apply_masks(cfg, mask_inputs, mask_segs)
        return engine.decide(feats, segs)

    candidate_inputs: List[str] = []
    candidate_segs: List[str] = []

    for _ in range(max_subset_size):
        flip_found = False
        # Try inputs
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
            return MufsResult(False, [], [])

        if decision_with_restored(candidate_inputs, candidate_segs) != h_restricted:
            break

    changed = True
    while changed:
        changed = False
        for key in list(candidate_inputs):
            tmp = [k for k in candidate_inputs if k != key]
            if decision_with_restored(tmp, candidate_segs) != h_restricted:
                candidate_inputs = tmp
                changed = True
        for sid in list(candidate_segs):
            tmp = [s for s in candidate_segs if s != sid]
            if decision_with_restored(candidate_inputs, tmp) != h_restricted:
                candidate_segs = tmp
                changed = True

    if not candidate_inputs and not candidate_segs:
        return MufsResult(False, [], [])
    return MufsResult(True, candidate_inputs, candidate_segs)


# ---------------- Demo data generation ---------------- #

def build_demo_trials(db: LAIZANeo4j, segment_score: Dict[str, float], n_trials: int = 10) -> List[TrialConfig]:
    rng = np.random.default_rng(123)
    feature_names = ["f1", "f2", "f3"]
    seg_ids = list(segment_score.keys())
    configs: List[TrialConfig] = []
    awareness_choices = ["IU", "PU", "MIX"]

    for _ in range(n_trials):
        features = {f: float(rng.normal()) for f in feature_names}
        segments = list(rng.choice(seg_ids, size=min(3, len(seg_ids)), replace=False))

        # Define hidden sets
        awareness = rng.choice(awareness_choices)
        hidden_inputs: List[str] = []
        hidden_segments: List[str] = []
        if awareness in ("IU", "MIX"):
            hidden_inputs = list(rng.choice(feature_names, size=1, replace=False))
        if awareness in ("PU", "MIX") and segments:
            hidden_segments = list(rng.choice(segments, size=1, replace=False))

        trial_id = db.create_trial(awareness, features, segments)
        configs.append(
            TrialConfig(
                trial_id=trial_id,
                features_full=features,
                segments_full=segments,
                hidden_inputs=hidden_inputs,
                hidden_segments=hidden_segments,
                awareness=awareness,
            )
        )
    return configs


def train_demo_model(feature_order: List[str], segment_order: List[str]) -> DecisionEngine:
    rng = np.random.default_rng(7)
    n = 200
    X = rng.normal(size=(n, len(feature_order) + len(segment_order)))
    # synthetic ground truth
    w = rng.normal(size=X.shape[1])
    y = (X.dot(w) + rng.normal(scale=0.3, size=n) > 0).astype(int)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    return DecisionEngine(model, feature_order, segment_order)


# ---------------- Main ---------------- #

def main() -> None:
    db = LAIZANeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        db.init_mufs_schema()
        segment_score = db.fetch_segment_potency()
        if not segment_score:
            print("No segments with potency found; run CR-001..3 pipelines first.")
            return

        configs = build_demo_trials(db, segment_score, n_trials=10)
        feature_order = ["f1", "f2", "f3"]
        segment_order = list(segment_score.keys())
        engine = train_demo_model(feature_order, segment_order)

        # Simple input importance heuristic: random weights
        rng = np.random.default_rng(99)
        input_score_global = {f: float(abs(rng.normal())) for f in feature_order}

        for cfg in configs:
            res = mufs_search(
                engine,
                cfg,
                input_score=input_score_global,
                segment_score=segment_score,
                max_subset_size=5,
            )
            if res.exists:
                mufs_type = (
                    "IU" if res.input_keys and not res.segment_ids
                    else "PU" if res.segment_ids and not res.input_keys
                    else "MIX"
                )
                db.create_mufs(cfg.trial_id, cfg.awareness, res.input_keys, res.segment_ids)
                db.mark_trial_intuition(
                    cfg.trial_id,
                    mufs_size=len(res.input_keys) + len(res.segment_ids),
                    has_mufs=True,
                    mufs_type=mufs_type,
                )
                print(f"Trial {cfg.trial_id} ({cfg.awareness}) MPG-Intuitive; MUFS inputs={res.input_keys}, segs={res.segment_ids}")
            else:
                db.mark_trial_intuition(cfg.trial_id, mufs_size=0, has_mufs=False, mufs_type="NONE")
                print(f"Trial {cfg.trial_id} ({cfg.awareness}) no MUFS found")
    finally:
        db.close()


if __name__ == "__main__":
    main()
