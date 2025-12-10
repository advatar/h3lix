**Change Request: CR-003 – Temporal MPG Dynamics, Full Potency Index & Noetic Hooks**

## Objective
- Represent the MPG as time-indexed with `:SegmentState` snapshots.
- Compute Impact Factors (RoC, Breadth of Impact, Amplification, Affective load, Gate leverage, Robustness) and aggregate into Potency Index.
- Add Noetic hooks by storing coherence per state and enabling queries for high-potency/low-coherence segments.

## Scope
- Neo4j schema: new label `:SegmentState` with constraint on `id`; relationship `(:Segment)-[:HAS_STATE]->(:SegmentState)`.
- Extend `scripts/mpg_rv_shap_demo.py` to create a `SegmentState` per segment per SHAP run.
- New `scripts/mpg_potency_index.py` to compute Impact Factors from history/topology, normalize, and write Potency back to `SegmentState` and `Segment`.
- Optional API hook to retrieve segment states for visualization/Mirror Core.

## Schema
`SegmentState` properties: `id`, `segment_id`, `t`, `rv`, `rv_score`, `coherence`, `roc`, `boi`, `amplification`, `affective_load`, `gate_leverage`, `robustness`, `potency`, `meta`, `created_at`, `demo`.
Constraint:
```cypher
CREATE CONSTRAINT segmentstate_id IF NOT EXISTS
FOR (s:SegmentState) REQUIRE s.id IS UNIQUE;
```

## Running
1) Run SHAP RV with states:
```bash
python scripts/mpg_rv_shap_demo.py
```
2) Compute Potency:
```bash
python scripts/mpg_potency_index.py
```
3) Inspect:
```cypher
MATCH (s:Segment {demo:true})-[:HAS_STATE]->(st:SegmentState)
RETURN s.id, st.t, st.rv, st.rv_score, st.potency
ORDER BY st.t DESC;
```

## Acceptance
- SegmentState snapshots exist and link to segments with time `t` and `rv_score`.
- Potency script computes and writes non-trivial impact factors and normalized potency to latest states and `Segment.potency_latest`.
- Coherence field available for Noetic integration; high-potency/low-coherence segments can be queried for Mirror Core.
