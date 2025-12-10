**Change Request: CR-002 – SHAP‑Backed Rogue Variable Detection & MPG API for Visualization**

## Objective
Extend CR-001 by:
- Using a prediction model + SHAP to detect Rogue Variables (RVs) per the paper (Shapley contributions, three-sigma rule).
- Treating lifted segments as structural variables and mapping SHAP values onto them.
- Exposing RV-tagged segments via FastAPI for visualization.

## Scope
- New script `scripts/mpg_rv_shap_demo.py`:
  - Reads level-1 `:Segment` nodes (demo) from Neo4j.
  - Builds synthetic decision data with one feature per segment.
  - Trains a tree model (RandomForest), computes SHAP values, applies three-sigma RV rule.
  - Updates Neo4j segments with `rv=true`, `rv_score`, `potency`.
- New API `api/mpg_api.py`:
  - Endpoints to list segments, RV segments, and segment edges for front-end visualization.

## Prereqs
- CR-001 run at least once to create level-1 `:Segment` nodes (`demo=true`).
- Neo4j running; env vars set: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (defaults bolt://localhost:7687, neo4j/neo4j-password).
- Python deps: `neo4j`, `networkx`, `numpy`, `pandas`, `scikit-learn`, `shap`, `fastapi`, `uvicorn`.

## Running SHAP RV demo
```bash
python scripts/mpg_rv_shap_demo.py
```
- Outputs model accuracy, RV threshold (mean + 3σ), and marks RV segments in Neo4j.
- Inspect: `MATCH (s:Segment {demo: true}) RETURN s;` and `MATCH (s:Segment {rv: true}) RETURN s;`.

## Running API
```bash
uvicorn api.mpg_api:app --reload
```
Endpoints:
- `/segments` – all demo segments with metrics and RV flags.
- `/segments/rv` – only segments flagged as RV.
- `/segments/edges` – lifted segment edges.

## Acceptance
- SHAP-backed RV detection flags at least one segment with `rv`, `rv_score`, `potency`.
- Three-sigma criterion applied to absolute SHAP contributions per segment variable.
- API serves segments, RVs, and edges for visualization.
