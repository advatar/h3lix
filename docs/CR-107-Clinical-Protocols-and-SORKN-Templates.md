# CR-107 – Clinical Protocol Templates & SORK-N Programs

This documents the protocol template model and endpoints introduced in CR-107.

## Neo4j schema

Add constraints:
```cypher
CREATE CONSTRAINT clinical_protocol_id IF NOT EXISTS FOR (p:ClinicalProtocol) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT protocol_module_id IF NOT EXISTS FOR (m:ProtocolModule) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT protocol_step_id IF NOT EXISTS FOR (s:ProtocolStep) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT outcome_measure_id IF NOT EXISTS FOR (o:OutcomeMeasure) REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT protocol_instance_id IF NOT EXISTS FOR (pi:ProtocolInstance) REQUIRE pi.id IS UNIQUE;
CREATE CONSTRAINT module_state_id IF NOT EXISTS FOR (ms:ModuleState) REQUIRE ms.id IS UNIQUE;
CREATE CONSTRAINT step_state_id IF NOT EXISTS FOR (ss:StepState) REQUIRE ss.id IS UNIQUE;
```

Relationships:
- `(ClinicalProtocol)-[:HAS_MODULE]->(ProtocolModule)-[:HAS_STEP]->(ProtocolStep)`
- `(ClinicalProtocol)-[:RECOMMENDS_OUTCOME]->(OutcomeMeasure)`
- `(InterventionPlan)-[:FOLLOWS_PROTOCOL]->(ClinicalProtocol)`
- `(InterventionPlan)-[:USES_MODULE]->(ProtocolModule)`
- `(InterventionPlan)-[:USES_STEP]->(ProtocolStep)`

## API usage

- List/view templates (clinician/researcher/admin roles):
  - `GET /clinical/protocols`
  - `GET /clinical/protocols/{id}`
- Instantiate a protocol for a participant (creates InterventionPlan, links modules/steps):
  - `POST /clinical/protocols/{id}/instantiate` with `{"participant_id": "P123"}`.

## Loading example protocols

- Run `python scripts/load_protocols.py` (uses `NEO4J_URI/USER/PASSWORD`) to load three templates:
  - Social Anxiety / Performance
  - Insomnia / Sleep Dysregulation
  - Decision Fatigue / Overcommitment
- Run `python scripts/add_protocol_constraints.py` to ensure ProtocolInstance/ModuleState/StepState constraints are in place.

## KMP / homework linkage

- Protocol steps may reference `kmp_task_template_id`; instantiated plans can be surfaced via `/mobile/therapy_tasks/{participant_id}`. Include `plan_id` when posting `/mobile/trial_result` to bind homework to the plan.

## Safety & scope

- Templates are assistive, low-risk CBT-like programs; clinicians remain in control.
- No diagnoses; avoid storing raw sensitive content in Neo4j. Use derived structures and Evidence.
