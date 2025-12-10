## Experiments (CR-009/CR-010)

- **E1 MPG-Intuition & MUFS vs baselines**  
  Config: `configs/e1_mpg_intuition.yaml` (conditions C0 baseline, C1 symbolic, C3 MPG/RV, C4 full H3LIX, restricted awareness).  
  Outputs: accuracy, Brier, MUFS rate, coherence-vs-accuracy corr.

- **E2 Coherence vs performance**  
  Config: `configs/e2_coherence.yaml` (C2 somatic-only, C3 MPG/RV, C4 full, C5 full+policy).  
  Outputs: accuracy, Brier, MUFS rate, coherence correlations.

- **E3 RV ablation**  
  Config: `configs/e3_rv_ablation.yaml` (A0 no ablation, A1 top-potency ablation, A2 random ablation).  
  Outputs: accuracy, Brier, MUFS rate, coherence correlations.

Run (synthetic placeholder metrics):
```
python experiments/runner.py --config configs/e1_mpg_intuition.yaml
python experiments/runner.py --config configs/e2_coherence.yaml
python experiments/runner.py --config configs/e3_rv_ablation.yaml
```

Neo4j nodes: `:Experiment`, `:ExperimentCondition`, `:ExperimentRun`, `:MetricResult`. Replace placeholder metric generators in `experiments/runner.py` with real evaluation hooks to Mirror Core stacks.
