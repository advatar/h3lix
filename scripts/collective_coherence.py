"""
CR-006: Group-level RV/Potency and coherence for Collective MPG.

This demo script:
- Loads CollectiveSegments.
- Builds a synthetic dataset per segment feature, trains a tree model, computes SHAP,
  and flags collective RVs with potency.
- Computes a simple group coherence score for GroupTrials (if present).
"""

from __future__ import annotations

import os
import statistics
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from neo4j import GraphDatabase
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import shap

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")
N_SAMPLES = 300


class CollectiveNeo4j:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def get_collective_segments(self) -> List[Dict[str, Any]]:
        records = self.run("MATCH (c:CollectiveSegment) RETURN c")
        return [dict(r["c"]) for r in records]

    def mark_collective_rv(self, cid: str, rv_score: float, potency: float) -> None:
        self.run(
            """
            MATCH (c:CollectiveSegment {id: $id})
            SET c.rv = true,
                c.rv_score = $rv_score,
                c.potency = $potency
            """,
            id=cid,
            rv_score=rv_score,
            potency=potency,
        )

    def clear_collective_rv(self) -> None:
        self.run(
            """
            MATCH (c:CollectiveSegment)
            REMOVE c.rv, c.rv_score
            """
        )

    def set_group_coherence(self, group_trial_id: str, coherence: float) -> None:
        self.run(
            """
            MATCH (gt:GroupTrial {id: $id})
            SET gt.coherence = $c
            """,
            id=group_trial_id,
            c=coherence,
        )

    def get_group_trials(self) -> List[Dict[str, Any]]:
        records = self.run("MATCH (gt:GroupTrial) RETURN gt")
        return [dict(r["gt"]) for r in records]


def build_dataset(collective_segments: List[Dict[str, Any]], n_samples: int = N_SAMPLES) -> pd.DataFrame:
    if not collective_segments:
        raise RuntimeError("No CollectiveSegment nodes found. Run collective_mpg_build.py first.")

    rng = np.random.default_rng(21)
    columns: List[str] = []
    feature_matrix = np.zeros((n_samples, len(collective_segments)))

    for j, seg in enumerate(collective_segments):
        cid = seg["id"]
        columns.append(f"cs_{cid}")
        base = (
            0.4 * float(seg.get("intensity", 0.0))
            + 0.4 * float(seg.get("confidence", 0.0))
            + 0.2 * float(seg.get("cohesion", 0.0))
        )
        feature_matrix[:, j] = base + rng.normal(0, 0.05, size=n_samples)

    # synthetic label with random weights
    weights = rng.normal(size=len(columns))
    logits = feature_matrix.dot(weights) + rng.normal(0, 0.5, size=n_samples)
    probs = 1 / (1 + np.exp(-logits))
    y = (probs > 0.5).astype(int)

    df = pd.DataFrame(feature_matrix, columns=columns)
    df["y"] = y
    return df


def simple_potency(rv_score: float, confidence: float, cohesion: float) -> float:
    return float(rv_score * (0.6 * confidence + 0.4 * cohesion))


def shap_collective_rv(db: CollectiveNeo4j, df: pd.DataFrame, collective_segments: List[Dict[str, Any]]) -> None:
    feature_cols = [c for c in df.columns if c.startswith("cs_")]
    X = df[feature_cols].values
    y = df["y"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    model = RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    print(f"Collective model train acc={model.score(X_train, y_train):.3f}, test acc={model.score(X_test, y_test):.3f}")

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)
    sv = shap_values[1] if isinstance(shap_values, list) and len(shap_values) == 2 else shap_values
    abs_contrib = np.abs(sv[0])
    mean_s = float(abs_contrib.mean())
    std_s = float(abs_contrib.std(ddof=1) if abs_contrib.size > 1 else 0.0)
    threshold = mean_s + 3 * std_s
    print(f"Collective RV threshold (mean+3σ): {threshold:.6f}")

    cid_lookup = {f"cs_{seg['id']}": seg for seg in collective_segments}
    db.clear_collective_rv()
    for col, contrib in zip(feature_cols, abs_contrib):
        if contrib >= threshold:
            seg = cid_lookup[col]
            conf = float(seg.get("confidence", 0.5))
            cohesion = float(seg.get("cohesion", 0.0))
            potency = simple_potency(contrib, conf, cohesion)
            db.mark_collective_rv(seg["id"], rv_score=float(contrib), potency=potency)
            print(f"CollectiveSegment {seg['id']} marked RV | contrib={contrib:.6f}, potency={potency:.6f}")


def compute_group_coherence(db: CollectiveNeo4j) -> None:
    trials = db.get_group_trials()
    if not trials:
        print("No GroupTrial nodes found; skipping coherence update.")
        return
    rng = np.random.default_rng(17)
    for gt in trials:
        potency_hint = float(gt.get("potency_hint", 0.5))
        coherence = 0.5 * potency_hint + float(rng.uniform(0, 0.5))
        db.set_group_coherence(gt["id"], coherence)
    print(f"Updated coherence for {len(trials)} group trials.")


def main() -> None:
    db = CollectiveNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        collective_segments = db.get_collective_segments()
        if not collective_segments:
            print("No CollectiveSegments found. Run collective_mpg_build.py first.")
            return
        df = build_dataset(collective_segments, n_samples=N_SAMPLES)
        shap_collective_rv(db, df, collective_segments)
        compute_group_coherence(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
