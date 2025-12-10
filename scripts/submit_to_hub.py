"""
Builds a submission payload from results/ and posts to the benchmark hub API.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests


def collect_results(results_root: Path, experiments: List[str]) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    for exp_id in experiments:
        exp_dir = results_root / exp_id
        if not exp_dir.exists():
            continue
        for summary_file in exp_dir.glob("*.json"):
            with summary_file.open() as f:
                data = json.load(f)
            collected.append(
                {
                    "experiment_id": exp_id,
                    "condition_id": data.get("condition", "unknown"),
                    "metrics": data.get("metrics", {}),
                }
            )
    return collected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team_id", required=True)
    parser.add_argument("--arch", required=True, help="Architecture name")
    parser.add_argument("--experiments", nargs="+", default=["E1_MPG_Intuition", "E2_Coherence_Performance", "E3_RV_Ablation"])
    parser.add_argument("--api_url", default="http://localhost:8000/benchmark/submit")
    args = parser.parse_args()

    results_root = Path("results")
    experiments = args.experiments
    exp_results = collect_results(results_root, experiments)

    payload = {
        "team_id": args.team_id,
        "architecture_name": args.arch,
        "experiments": exp_results,
        "notes": "Auto-generated submission from local runs",
    }

    resp = requests.post(args.api_url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"Submission accepted: {resp.json()}")


if __name__ == "__main__":
    main()
