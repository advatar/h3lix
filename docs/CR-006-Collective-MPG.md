**Change Request: CR-006 – Multi-Participant / Collective MPG, Cross-Participant Echoes & Group Coherence**

## Objective
- Extend single-participant MPG to collective settings with cross-participant echoes and a Collective MPG.
- Compute group-level RV/Potency and Noetic coherence; relate individual MUFS/intuition to group patterns.

## Schema
- New labels/constraints: `Group`, `GroupSession`, `GroupTrial`, `CollectiveSegment`.
- Echo links: `(:Segment)-[:ECHO_SEGMENT {similarity, basis}]->(:Segment)` across participants.
- Collective graph: `CollectiveSegment` nodes with `member_segment_ids`, `participant_ids`, aggregated valence/intensity/confidence/cohesion/potency, and `rv` flags; edges aggregated from member segment edges.
- Relationships: `(Group)-[:HAS_GROUP_SESSION]->(GroupSession)`, `(GroupSession)-[:HAS_GROUP_TRIAL]->(GroupTrial)`, `(GroupSession)-[:INCLUDES_SESSION]->(Session)`, `(GroupTrial)-[:ALIGNS_TRIAL]->(Trial)`, `(CollectiveSegment)-[:AGGREGATES]->(Segment)`.

## Code
- `scripts/collective_mpg_build.py`: detects echo segments (cosine similarity on segment properties), writes `ECHO_SEGMENT`, clusters into `CollectiveSegment`, and builds collective edges.
- `scripts/collective_coherence.py`: computes group-level SHAP RVs for CollectiveSegments on synthetic data, marks `rv/rv_score/potency`, and sets simple coherence on GroupTrials (if present).
- `api/collective_api.py`: endpoints to list collective segments/RVs and fetch group coherence/trial details; included in `api/main.py`.

## Running
1) Ensure individual segments exist with `participant_id` set. Run echo/collective build:
   ```bash
   python scripts/collective_mpg_build.py
   ```
2) Compute group RV/potency and coherence:
   ```bash
   python scripts/collective_coherence.py
   ```
3) Start API (`uvicorn api.main:app --reload`) and query `/collective/segments`, `/collective/segments/rv`, `/collective/coherence/{group_session_id}`, `/collective/trials/{group_trial_id}`.
4) Demo creds: defaults use `NEO4J_USER=neo4j` / `NEO4J_PASSWORD=neo4j-password`; replace for production deployments.

## Acceptance (per CR-006)
- CollectiveSegment nodes exist from echoed segments across ≥2 participants; collective edges built.
- Collective RVs/potency computed; coherence stored for GroupTrials when present.
- API exposes collective segments, RVs, coherence series, and trial details for group analysis.
