## Benchmark Hub (CR-011)

Purpose: let teams run canonical MPG-Intuition experiments (E1–E3) and submit results for a lightweight leaderboard.

### Submission format
- POST body to `/benchmark/submit` (FastAPI) with:
  ```json
  {
    "team_id": "lab_xyz",
    "architecture_name": "H3LIX_FULL",
    "contact": "lab@xyz.edu",
    "experiments": [
      {
        "experiment_id": "E1_MPG_Intuition",
        "condition_id": "C4",
        "metrics": {
          "accuracy": 0.78,
          "brier": 0.19,
          "has_mufs_rate": 0.6,
          "coherence_vs_accuracy_corr": 0.3
        }
      }
    ],
    "notes": "Synthetic run using canonical configs"
  }
  ```
- Optional per-run JSON from `results/` can be included via `payload["runs"]`. Submissions are validated against `schemas/manifest.schema.json` and stored in SQLite at `results/leaderboard.db`.

### Leaderboard
- GET `/benchmark/leaderboard/{experiment_id}` returns stored submissions for that experiment (persisted in SQLite DB at `results/leaderboard.db`).

### Workflow
1. Run experiments locally with canonical configs (E1–E3).
2. Use `scripts/submit_to_hub.py` to package `results/` into a submission and POST to the hub.
3. Check leaderboard via GET.

### Ethics
- Synthetic/anonymized data only. No participant-identifiable traces. Demo credentials (`neo4j/neo4j-password`) must be replaced for shared deployments.
