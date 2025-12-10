**Change Request: CR-001 – Minimal H3LIX MPG Prototype in Python + Neo4j**

This document mirrors the CR requirements for a vertical slice of the MPG/LAIZA prototype.

## Objective
- Build a runnable Python + Neo4j prototype that:
  1) Creates a Level-0 Layer-Type Graph in Neo4j.
  2) Segments the graph in NetworkX and applies Lift to produce Level-1 segments.
  3) Runs a simple Rogue Variable (RV) detection over segments using a three-sigma rule.

## Schema (Definition 1, Eq. 1)
- Labels: `:MPGNode`, `:Segment`, `:Evidence`.
- Relationships: subset of Σ_E (e.g., `CAUSES`, `TRIGGERS`, `CONTRADICTS`, etc.).
- Constraints / indexes:
  ```cypher
  CREATE CONSTRAINT mpgnode_id IF NOT EXISTS FOR (n:MPGNode) REQUIRE n.id IS UNIQUE;
  CREATE CONSTRAINT segment_id IF NOT EXISTS FOR (s:Segment) REQUIRE s.id IS UNIQUE;
  CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE;
  CREATE INDEX mpgnode_level IF NOT EXISTS FOR (n:MPGNode) ON (n.level);
  ```
- Node/segment properties: `id, name, layers, valence, intensity, recency, stability, importance, confidence, reasoning, level, rv, rv_score, potency`.
- Relationship properties: `strength, confidence, description`.
- Evidence properties: `id, description, source_type, pointer, snippet, c, q, u, t`.

## Prototype script (scripts/mpg_demo.py)
- Connects to Neo4j, initializes schema, and clears previous demo data (`demo = true`).
- Inserts a toy Level-0 MPG (5–8 nodes, 6–12 edges) inspired by Figures 1–3 of the paper.
- Loads the graph into NetworkX, segments it using strong edges, and writes Level-1 `:Segment` nodes plus inter-segment edges back to Neo4j.
- Computes RVs over segments with contributions = `importance * confidence`; marks segments with `rv = true` when contribution ≥ mean + 3σ, setting `rv_score` and `potency`.

## Running
1. Ensure Neo4j is running and set `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (defaults to bolt://localhost:7687, neo4j/neo4j-password).
2. Install deps: `pip install neo4j networkx`.
3. Execute: `python scripts/mpg_demo.py`.
4. Inspect:
   - `MATCH (n:MPGNode {demo: true}) RETURN n;`
   - `MATCH (s:Segment {demo: true}) RETURN s;`
   - `MATCH (s:Segment {rv: true}) RETURN s;`

## Acceptance Criteria
- Constraints exist for MPGNode, Segment, Evidence; level index present.
- Running the script creates ~5 Level-0 nodes and ~5–8 edges with `demo = true`.
- Lift produces Level-1 `:Segment` nodes with `members` populated and inter-segment edges when base edges cross segments.
- RV detection applies three-sigma criterion (Definition 6) and tags high-impact segments with `rv`, `rv_score`, `potency`.

## Notes / Limitations
- RV uses synthetic contributions (importance × confidence) instead of SHAP for this slice.
- Segmentation uses strength-threshold connected components; more advanced community detection is recommended for production.
