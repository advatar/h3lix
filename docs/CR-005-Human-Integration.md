**Change Request: CR-005 – Human-in-the-Loop LAIZA Integration & MPG-Intuition**

## Objective
- Add human participants/sessions/trials with self-report and awareness checks.
- Run system + human in parallel under FULL vs restricted (IU/PU/MIX), and label MPG-Intuitive trials via MUFS (CR-004).
- Link somatic summaries and coherence/potency for analysis of intuition.

## Schema (Neo4j)
- Constraints: `participant_id`, `session_id`, `trial_id`, `selfreport_id`, `awarenesscheck_id`, `mufs_id`.
- Nodes: `Participant`, `Session`, `Trial` (extended with awareness, human/system decisions, MUFS flags), `SelfReport`, `AwarenessCheck`, `MUFS`.
- Relationships: `(Participant)-[:HAS_SESSION]->(Session)`, `(Session)-[:HAS_TRIAL]->(Trial)`, `(Trial)-[:HAS_SELF_REPORT]->(SelfReport)`, `(Trial)-[:HAS_AWARENESS_CHECK]->(AwarenessCheck)`, `(Trial)-[:HAS_MUFS]->(MUFS)`, `(MUFS)-[:INCLUDES_SEGMENT]->(Segment)`.

## Code components
- `experiments/human_runner.py`: Neo4j helpers, trial runner to log human data, run system decisions, perform MUFS search, and mark MPG-Intuitive trials.
- `api/human_api.py`: FastAPI routes for participant/session/trial creation, human response updates, self-reports, awareness checks.
- `analysis/human_mpg_intuition.ipynb`: starter queries for MUFS incidence and coherence/intuition correlations.
- `api/main.py`: includes human router; other APIs unchanged.

## Running
1) Ensure CR-001..4 pipelines ran and Neo4j is running (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` envs). Demo defaults use `neo4j/neo4j-password`; replace with production secrets outside sandbox.
2) Start API: `uvicorn api.main:app --reload`.
3) Create participants/sessions/trials via `/human` endpoints; log human responses and self-reports.
4) Run MUFS/potency scripts as before; analyze with the notebook for MUFS incidence vs awareness/coherence/potency.

## Notes
- Somatic summaries should be attached as Evidence to Trials/Segments (channels processed externally).
- Privacy/ethics: keep Participant IDs pseudonymous; handle consent and data access controls separately.
