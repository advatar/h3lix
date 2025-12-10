**Change Request: CR-004 – MUFS Search & MPG-Intuition Experiment Harness**

## Objective
- Implement MUFS (Minimal Unaware Flip Set) search for restricted trials (IU/PU/MIX).
- Label trials as MPG-Intuitive when a nonempty MUFS exists.
- Store MUFS and awareness metadata in Neo4j, wired to segments and trials.
- Provide a Python harness and API hooks to query MUFS incidence and its relation to Potency/coherence.

## Schema additions
- Trial fields: `awareness_condition` (FULL/IU/PU/MIX), `mask_type`, `has_mufs`, `mufs_size`, `mufs_type`, `mpg_intuitive`.
- MUFS node with constraint:
  ```cypher
  CREATE CONSTRAINT mufs_id IF NOT EXISTS FOR (m:MUFS) REQUIRE m.id IS UNIQUE;
  ```
  Properties: `id`, `trial_id`, `awareness_condition`, `size`, `input_keys`, `created_at`.
  Relations: `(Trial)-[:HAS_MUFS]->(MUFS)` and `(MUFS)-[:INCLUDES_SEGMENT]->(Segment)`.

## Scripts
- `scripts/mufs_search_demo.py`:
  - Defines `DecisionEngine`, masking utilities (IU/PU), and a greedy+minimal MUFS search.
  - Simulates trials with full vs restricted awareness, uses segment potency as process importance, and stores MUFS + trial flags in Neo4j.
- Neo4j helper to set awareness defaults and create MUFS nodes.

## API
- Extend FastAPI (`api/mpg_api.py`) with MUFS/trial intuition endpoints if needed (added `/trials/intuition` and `/mufs`).

## Running
1) Ensure CR-001..3 are applied; Neo4j running.
2) Seed some trials (demo script generates synthetic).
3) Run MUFS search:
   ```bash
   python scripts/mufs_search_demo.py
   ```
4) Inspect:
   ```cypher
   MATCH (t:Trial)-[:HAS_MUFS]->(m:MUFS) RETURN t.id, t.awareness_condition, t.mpg_intuitive, m.size;
   ```

## Acceptance
- MUFS search finds flip sets (inputs/segments) for restricted trials and marks `Trial.mpg_intuitive`.
- MUFS nodes exist with links to segments and trials; trial fields reflect MUFS size/type.
- API exposes MUFS/intuition data for downstream visualization/analysis.
