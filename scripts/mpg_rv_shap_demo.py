"""
CR-002/CR-003: SHAP-backed Rogue Variable detection on MPG segments, plus
SegmentState snapshots for temporal MPG_t.

Prereqs:
- CR-001 executed so level-1 :Segment nodes with demo=true exist in Neo4j.
- Neo4j reachable via env vars NEO4J_URI/USER/PASSWORD (defaults to local docker).
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from neo4j import GraphDatabase
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import shap

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")
N_SAMPLES = 500  # synthetic trials


class MPGNeo4j:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def init_segmentstate_schema(self) -> None:
        self.run(
            """
            CREATE CONSTRAINT segmentstate_id IF NOT EXISTS
            FOR (s:SegmentState) REQUIRE s.id IS UNIQUE;
            """
        )

    def get_demo_segments(self) -> List[Dict[str, Any]]:
        return self.run(
            """
            MATCH (s:Segment)
            WHERE s.demo = true
            RETURN s.id AS id,
                   coalesce(s.importance, 0.5) AS importance,
                   coalesce(s.confidence, 0.5) AS confidence,
                   coalesce(s.valence, 0.0) AS valence
            """
        )

    def mark_segment_as_rv(self, seg_id: str, rv_score: float, potency: float) -> None:
        self.run(
            """
            MATCH (s:Segment {id: $id})
            SET s.rv = true,
                s.rv_score = $rv_score,
                s.potency = $potency
            """,
            id=seg_id,
            rv_score=float(rv_score),
            potency=float(potency),
        )

    def clear_rv_flags(self) -> None:
        self.run(
            """
            MATCH (s:Segment)
            WHERE s.demo = true
            REMOVE s.rv, s.rv_score, s.potency
            """
        )

    def create_segment_state(
        self,
        seg_id: str,
        t_value: float,
        rv: bool,
        rv_score: float,
        coherence: float | None = None,
    ) -> str:
        state_id = str(uuid.uuid4())
        self.run(
            """
            MATCH (s:Segment {id: $seg_id})
            CREATE (st:SegmentState {
                id: $id,
                segment_id: $seg_id,
                t: $t,
                rv: $rv,
                rv_score: $rv_score,
                coherence: $coherence,
                roc: 0.0,
                boi: 0.0,
                amplification: 0.0,
                affective_load: 0.0,
                gate_leverage: 0.0,
                robustness: 0.0,
                potency: 0.0,
                meta: {},
                created_at: datetime(),
                demo: true
            })
            CREATE (s)-[:HAS_STATE]->(st)
            """,
            seg_id=seg_id,
            id=state_id,
            t=t_value,
            rv=rv,
            rv_score=float(rv_score),
            coherence=coherence,
        )
        return state_id


def build_segment_feature_matrix(db: MPGNeo4j, n_samples: int = N_SAMPLES) -> Tuple[pd.DataFrame, List[str]]:
    """Create synthetic dataset with one feature per segment."""
    records = db.get_demo_segments()
    if not records:
        raise RuntimeError("No demo segments found. Run CR-001 lift first.")

    seg_ids = [r["id"] for r in records]
    importance = {r["id"]: float(r["importance"]) for r in records}
    confidence = {r["id"]: float(r["confidence"]) for r in records}
    valence = {r["id"]: float(r["valence"]) for r in records}

    rng = np.random.default_rng(42)
    driver_ids = rng.choice(seg_ids, size=min(3, len(seg_ids)), replace=False)
    print("Ground-truth driver segments (synthetic):", list(driver_ids))

    X = np.zeros((n_samples, len(seg_ids)))
    columns: List[str] = []
    for j, seg_id in enumerate(seg_ids):
        feat_name = f"seg_{seg_id}"
        columns.append(feat_name)
        base = (
            0.5 * importance[seg_id]
            + 0.3 * confidence[seg_id]
            + 0.2 * max(valence[seg_id], 0.0)
        )
        X[:, j] = base + rng.normal(0, 0.05, size=n_samples)

    weights = np.zeros(len(seg_ids))
    for j, seg_id in enumerate(seg_ids):
        weights[j] = rng.uniform(1.0, 2.0) if seg_id in driver_ids else rng.uniform(-0.2, 0.2)

    logits = X.dot(weights) + rng.normal(0, 0.5, size=n_samples)
    probs = 1 / (1 + np.exp(-logits))
    y = (probs > 0.5).astype(int)

    df = pd.DataFrame(X, columns=columns)
    df["y"] = y
    return df, seg_ids


def simple_potency(rv_score: float, importance: float, confidence: float) -> float:
    """Simplified potency as contribution scaled by importance/confidence."""
    return float(rv_score * (0.5 * importance + 0.5 * confidence))


def shap_rv_detection(db: MPGNeo4j, df: pd.DataFrame, seg_ids: List[str]) -> None:
    """Compute SHAP contributions and apply three-sigma RV rule."""
    feature_cols = [c for c in df.columns if c.startswith("seg_")]
    X = df[feature_cols].values
    y = df["y"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    print(f"Train accuracy: {model.score(X_train, y_train):.3f}")
    print(f"Test accuracy : {model.score(X_test, y_test):.3f}")

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)
    sv = shap_values[1] if isinstance(shap_values, list) and len(shap_values) == 2 else shap_values

    instance_sv = sv[0]
    abs_contrib = np.abs(instance_sv)
    mean_s = float(abs_contrib.mean())
    std_s = float(abs_contrib.std(ddof=1) if abs_contrib.size > 1 else 0.0)
    threshold = mean_s + 3 * std_s
    print(f"RV threshold (mean + 3σ): {threshold:.6f}")

    feature_to_seg = {j: col[len("seg_"):] for j, col in enumerate(feature_cols)}
    db.clear_rv_flags()

    t_value = time.time()

    for j, contrib in enumerate(abs_contrib):
        seg_id = feature_to_seg[j]
        recs = db.run(
            """
            MATCH (s:Segment {id: $id})
            RETURN coalesce(s.importance, 0.5) AS importance,
                   coalesce(s.confidence, 0.5) AS confidence
            """,
            id=seg_id,
        )
        imp = float(recs[0]["importance"]) if recs else 0.5
        conf = float(recs[0]["confidence"]) if recs else 0.5
        is_rv = contrib >= threshold

        if is_rv:
            potency = simple_potency(contrib, imp, conf)
            db.mark_segment_as_rv(seg_id, rv_score=float(contrib), potency=potency)
            print(
                f"Segment {seg_id} marked RV | contrib={contrib:.6f}, "
                f"importance={imp:.3f}, confidence={conf:.3f}, potency={potency:.6f}"
            )

        db.create_segment_state(
            seg_id=seg_id,
            t_value=t_value,
            rv=is_rv,
            rv_score=float(contrib),
            coherence=None,
        )


def main() -> None:
    db = MPGNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        db.init_segmentstate_schema()
        df, seg_ids = build_segment_feature_matrix(db, n_samples=N_SAMPLES)
        shap_rv_detection(db, df, seg_ids)
        print("SHAP-based RV detection finished.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
