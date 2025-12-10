**Change Request: CR-007 – Policy Learning over (Collective) MPG for Safe, Auditable Interventions**

## Objective
- Use RVs + Potency + coherence to prioritize intervention targets.
- Learn safe, auditable interventions via contextual bandits/RL light.
- Keep all actions logged to Neo4j with governance hooks.

## Schema (Neo4j)
- Constraints: `policy_id`, `policy_episode_id`, `policy_outcome_id`, plus `InterventionType`.
- Nodes:
  - `InterventionType {id, name, layer_target, risk_level, description, parameters_schema, active}`
  - `Policy {id, name, description, version}`
  - `PolicyEpisode {id, policy_id, trial_id, context_hash, rv_segment_ids, collective_segment_ids, chosen_intervention_id, parameters, human_override, override_type, timestamp}`
  - `PolicyOutcome {id, episode_id, reward, delta_coherence, delta_accuracy, delta_rt, notes}`
- Relationships:
  - `(Policy)-[:USES_INTERVENTION]->(InterventionType)`
  - `(Policy)-[:HAS_EPISODE]->(PolicyEpisode)`
  - `(PolicyEpisode)-[:FOR_TRIAL]->(Trial)`
  - `(PolicyEpisode)-[:APPLIED_INTERVENTION]->(InterventionType)`
  - `(PolicyEpisode)-[:HAS_OUTCOME]->(PolicyOutcome)`
  - Optional `(Policy)-[:RUNS_ON_GROUP]->(Group)` / `(Policy)-[:RUNS_ON_PARTICIPANT]->(Participant)`.

## Code
- `policies/contextual_bandit.py`: Linear UCB bandit for action selection and updates.
- `policies/policy_engine.py`: wraps bandit + Neo4j logging (episodes/outcomes), builds context vectors from RV/potency/coherence.
- `api/policy_api.py`: endpoints `/policy/recommend` and `/policy/feedback`.
- Mirror Core: call policy engine in N→S′ to select intervention and update with observed reward.

## Actions (demo whitelist)
- `SLOW_DECISION`, `REQUEST_JUSTIFICATION`, `SURFACE_EVIDENCE`, `FOCUS_SEGMENT`, `DEFOCUS_SEGMENT`, `TAKE_BREAK`, `SOFT_ALERT`.
- Risk levels: LOW/MEDIUM only; parameters bounded.

## Reward (demo)
`reward = w_c*ΔC + w_acc*Δacc + w_cal*Δcal − w_rt*(Δrt/baseline_rt)`, clipped to [-1,1]; log all components in PolicyOutcome for audit.

## Running (demo flow)
1) Ensure Neo4j running (demo creds: `neo4j/neo4j-password`); apply constraints via policy scripts.
2) Seed `InterventionType` and a `Policy`.
3) In trials, build context from RV/SegmentState/coherence, call policy engine to recommend; log episode.
4) After outcome, compute reward, call feedback endpoint to update bandit + PolicyOutcome.

## Safety/governance
- Whitelist actions; disallow high-risk; track `human_override`/`override_type`.
- Audit: all episodes/outcomes stored; override rates can down-rank actions.

## Acceptance (per CR-007)
- Policy schema present; episodes/outcomes linked to trials and interventions.
- Bandit can select/update actions from contexts; Mirror Core integrated for N→S′ decisions.
- API supports recommend/feedback; logs are auditable; overrides tracked.
