**Change Request: CR-011 – External Benchmark Hub & MPG-Intuition Leaderboard**

## Objective
- Enable external teams to run canonical MPG-Intuition experiments (E1–E3) and submit results for comparison.
- Provide submission format, validation, and leaderboard endpoints.

## Implementation
- Benchmark hub API (`api/benchmark_hub.py`):
  - `POST /benchmark/submit` validates against `schemas/manifest.schema.json` and stores submissions in SQLite (`results/leaderboard.db`).
  - `GET /benchmark/leaderboard/{experiment_id}` returns filtered submissions.
- Submission helper `scripts/submit_to_hub.py` packages `results/` summaries and posts to the hub.
- Docs: `docs/BENCHMARK_HUB.md` (format, workflow, ethics); schema files in `schemas/`.

## Usage
1) Run experiments via configs (E1–E3) to populate `results/`.
2) Submit: `python scripts/submit_to_hub.py --team_id demo --arch H3LIX_FULL`.
3) Query leaderboard: `GET /benchmark/leaderboard/E1_MPG_Intuition`.

## Notes
- Synthetic/anonymized data only. Replace demo creds (`neo4j/neo4j-password`) for shared deployments.
- SQLite persistence is local; swap to Neo4j/SQL for multi-user hosting.
