**Change Request: CR-009 – Formal Evaluation, Benchmarks & Ablations for H3LIX/LAIZA**

## Objective
- Add a reproducible benchmark layer: experiments, configs, runs, metrics.
- Compare H3LIX stacks vs baselines and ablations for MPG, MUFS, coherence, policies.

## Schema (Neo4j)
- Constraints: `experiment_id`, `expt_condition_id`, `expt_run_id`, `metricresult_id`.
- Nodes:
  - `Experiment {id, name, description, prereg_link, created_at}`
  - `ExperimentCondition {id, name, stack, awareness_mode, notes}`
  - `ExperimentRun {id, seed, n_trials, status, started_at, ended_at}`
  - `MetricResult {id, name, value, ci_lower, ci_upper, p_value, details}`
- Relationships:
  - `(Experiment)-[:HAS_CONDITION]->(ExperimentCondition)`
  - `(ExperimentCondition)-[:HAS_RUN]->(ExperimentRun)`
  - `(ExperimentRun)-[:HAS_METRIC]->(MetricResult)`

## Files/Code
- `experiments/registry.py`: helpers to create Experiments/Conditions/Runs/MetricResults in Neo4j.
- `experiments/runner.py`: loads YAML configs, runs conditions via stack variants, logs runs/metrics.
- `configs/` YAMLs for E1–E3 starter experiments.
- Analysis notebooks: `analysis/e1_e2_intuition_coherence.ipynb`, `analysis/e3_rv_ablation.ipynb`, `analysis/e4_e5_policies_generalization.ipynb`.

## Experiment families (configs provided)
- E1: MPG-Intuition & MUFS vs baselines (C0/C1/C3/C4).
- E2: Coherence vs performance/calibration (C2–C5).
- E3: RV/Potency ablations vs random (A0/A1/A2).
- E4/E5 placeholders for policy/generalization (doc references, configs can extend).

## Running (demo)
1) Ensure Neo4j running (demo creds `neo4j/neo4j-password`); start API if needed.
2) Create an experiment via `experiments/registry.py` or let `runner.py` do it from config.
3) Run: `python experiments/runner.py --config configs/e1_mpg_intuition.yaml` (similar for e2/e3).
4) Inspect results in Neo4j (`:Experiment`, `:ExperimentRun`, `:MetricResult`) and notebooks.

## Pre-reg & power
- Include prereg info in `Experiment.prereg_link`; templates for hypotheses/analysis/power provided separately.
- Power analysis can be added as a separate script (Monte Carlo) to size runs/trials.

## Acceptance
- Experiment registry populated from YAML configs; runs/metrics recorded.
- At least E1–E3 can execute end-to-end: config → runs → metrics → notebook plots.
- MPG-Intuition, coherence, and RV ablation claims testable via scripts/notebooks.
- Reproducibility: fixed seeds reproduce; ablations change metrics sensibly.
