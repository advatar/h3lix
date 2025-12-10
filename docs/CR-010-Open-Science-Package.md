**Change Request: CR-010 – Open-Science Reference Package & Reproducible Demo**

## Objective
- Package CR-001..CR-009 into a reproducible, shareable demo stack (synthetic data) with one-command experiments (E1–E3), containerized services, and clear ethical guidance.

## Scope delivered here
- Documentation stubs for open-science packaging (`README.md`, `docs/EXPERIMENTS.md`, `docs/ETHICS_PRIVACY.md`).
- Config-driven experiment runner (CR-009) already present; reuse `configs/e1_mpg_intuition.yaml`, `e2_coherence.yaml`, `e3_rv_ablation.yaml`.
- Demo credentials remain `NEO4J_USER=neo4j`, `NEO4J_PASSWORD=neo4j-password` for local use; replace for real deployments.
- Containerization guidance (compose skeleton) captured in docs; actual compose files can be added alongside when ready.

## Quickstart (local, synthetic)
1) Ensure Neo4j running (demo docker: `docker run -d --name neo4j-h3lix -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/neo4j-password neo4j:5.22`).
2) Export env:
   ```
   export NEO4J_URI=bolt://localhost:7687
   export NEO4J_USER=neo4j
   export NEO4J_PASSWORD=neo4j-password
   ```
3) Run an experiment config (synthetic placeholder metrics):
   ```
   python experiments/runner.py --config configs/e1_mpg_intuition.yaml
   ```
4) Inspect Neo4j for `:Experiment`, `:ExperimentRun`, `:MetricResult` or adapt notebooks under `analysis/`.

## Files added
- `docs/EXPERIMENTS.md` – mapping of configs to CR-009 experiment families.
- `docs/ETHICS_PRIVACY.md` – synthetic-only default; requirements for any real human data.
- Root `README.md` – quickstart, structure, demo creds note.

## Notes
- Demo datasets are not embedded; use synthetic generators or local stubs. Do not add real human data without IRB/consent and a privacy review.
- Container skeleton (compose) is described in CR-010; add `docker/` assets when ready.
