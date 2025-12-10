"""
CR-009: Experiment runner loading YAML configs and executing conditions.
This is a scaffold: replace placeholders with actual task execution + metric computation.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import yaml

from experiments.registry import ExperimentRegistry
from noetic.coherence import coherence_score
from experiments.human_runner import DecisionEngine, mufs_search
from tests.test_mufs import DummyModel  # reuse simple model for MUFS-like search


@dataclass
class ConditionConfig:
    id: str
    stack: str
    awareness_mode: str
    notes: str | None = None


@dataclass
class ExperimentConfig:
    id: str
    description: str
    tasks: List[Dict[str, Any]]
    conditions: List[ConditionConfig]
    n_runs: int
    n_trials_per_run: int
    metrics: List[str]


def load_config(path: str) -> ExperimentConfig:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    conditions = [
        ConditionConfig(
            id=c["id"],
            stack=c["stack"],
            awareness_mode=c.get("awareness_mode", "FULL"),
            notes=c.get("notes"),
        )
        for c in cfg.get("conditions", [])
    ]
    return ExperimentConfig(
        id=cfg["id"],
        description=cfg.get("description", ""),
        tasks=cfg.get("tasks", []),
        conditions=conditions,
        n_runs=cfg.get("n_runs", 1),
        n_trials_per_run=cfg.get("n_trials_per_run", 10),
        metrics=cfg.get("metrics", []),
    )


def load_trials(dataset_path: str, n_trials: int) -> List[Dict[str, Any]]:
    trials: List[Dict[str, Any]] = []
    path = Path(dataset_path)
    if path.exists():
        with path.open() as f:
            for line in f:
                try:
                    trials.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if not trials:
        rng = np.random.default_rng(42)
        for i in range(n_trials):
            feats = rng.normal(size=3).tolist()
            difficulty = float(rng.uniform(0, 1))
            label = int((np.dot(feats, [0.4, -0.3, 0.2]) + rng.normal() > 0))
            trials.append({"id": f"gen-{i}", "features": feats, "difficulty": difficulty, "label": label})
    return trials[:n_trials]


def evaluate_condition(condition: ConditionConfig, trials: List[Dict[str, Any]], rng: random.Random) -> Dict[str, float]:
    # Simple synthetic evaluator: probability based on features and condition stack, plus coherence and MUFS-like flag.
    feature_order = ["f1", "f2", "f3"]
    segment_order = ["s1"]
    model = DummyModel(bias=0.0)
    engine = DecisionEngine(model, feature_order, segment_order)

    preds = []
    labels = []
    coherences = []
    mufs_flags = []
    per_trial: List[Dict[str, Any]] = []
    for tr in trials:
        feats = tr["features"]
        label = int(tr["label"])
        # stack-specific bias
        stack_bonus = {
            "BASELINE": -0.1,
            "SYMBOLIC_ONLY": -0.05,
            "H3LIX_SOMATIC_ONLY": 0.02,
            "H3LIX_MPG_RV": 0.08,
            "H3LIX_FULL": 0.12,
            "H3LIX_FULL_POLICY": 0.14,
        }.get(condition.stack, 0.0)
        logit = float(0.5 * feats[0] + 0.3 * feats[1] - 0.2 * feats[2] + stack_bonus + rng.normal(0, 0.1))
        prob = 1 / (1 + np.exp(-logit))
        pred = 1 if prob >= 0.5 else 0
        preds.append(pred)
        labels.append(label)
        # synthetic coherence using coherence_score on a tiny matrix
        feature_matrix = np.array([[prob, stack_bonus, feats[0]]])
        coherence = coherence_score(feature_matrix)
        coherences.append(coherence)
        # MUFS-like flag: use mufs_search with hidden segment if stack includes MPG
        hidden_segments = ["s1"] if "MPG" in condition.stack else []
        res = mufs_search(
            engine,
            features_full={"f1": feats[0], "f2": feats[1], "f3": feats[2]},
            segments_full=["s1"],
            hidden_inputs=[],
            hidden_segments=hidden_segments,
            input_score={},
            segment_score={"s1": 1.0},
            max_subset_size=2,
        )
        mufs_flag = res.exists
        mufs_flags.append(mufs_flag)
        per_trial.append(
            {
                "id": tr["id"],
                "label": label,
                "pred": pred,
                "prob": prob,
                "coherence": coherence,
                "mufs": mufs_flag,
            }
        )

    labels_arr = np.array(labels, dtype=float)
    preds_arr = np.array(preds, dtype=float)
    acc = float((labels_arr == preds_arr).mean())
    brier = float(np.mean((preds_arr - labels_arr) ** 2))
    has_mufs_rate = float(np.mean(mufs_flags))
    if np.std(labels_arr) == 0 or np.std(coherences) == 0:
        corr = 0.0
    else:
        corr = float(np.corrcoef(coherences, labels_arr == preds_arr)[0, 1])
    return {
        "accuracy": acc,
        "brier": brier,
        "has_mufs_rate": has_mufs_rate,
        "coherence_vs_accuracy_corr": corr,
        "per_trial": per_trial,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to YAML experiment config")
    args = parser.parse_args()

    cfg = load_config(args.config)
    registry = ExperimentRegistry()
    registry.init_schema()

    exp_id = registry.create_experiment(cfg.id, cfg.description, prereg_link=None)
    cond_ids = {}
    for cond in cfg.conditions:
        cid = registry.create_condition(exp_id, cond.id, cond.stack, cond.awareness_mode, notes=cond.notes)
        cond_ids[cond.id] = cid

    results_root = Path("results") / cfg.id
    results_root.mkdir(parents=True, exist_ok=True)

    dataset_path = cfg.tasks[0].get("dataset") if cfg.tasks else ""
    for cond in cfg.conditions:
        for run_idx in range(cfg.n_runs):
            seed = run_idx + 1
            rng = random.Random(seed)
            trials = load_trials(dataset_path, cfg.n_trials_per_run)
            run_id = registry.create_run(cond_ids[cond.id], seed=seed, n_trials=len(trials))
            metrics = evaluate_condition(cond, trials, rng)
            for name, value in metrics.items():
                if name == "per_trial":
                    continue
                registry.add_metric(run_id, name=name, value=float(value))
            registry.finish_run(run_id, status="COMPLETED")
            result_path = results_root / f"{cond.id}_run{run_idx+1}.json"
            with result_path.open("w") as f:
                json.dump({"condition": cond.id, "run": run_idx + 1, "metrics": {k: v for k, v in metrics.items() if k != "per_trial"}}, f, indent=2)
            # per-trial log
            trials_path = results_root / f"{cond.id}_run{run_idx+1}_trials.json"
            with trials_path.open("w") as f:
                json.dump(metrics.get("per_trial", []), f, indent=2)
            print(f"Completed run {run_id} for condition {cond.id}, saved {result_path} and {trials_path}")


if __name__ == "__main__":
    main()
