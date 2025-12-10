# Clinical “Guided Mode” (CR-106) – usage notes

## API overview

- Start/end sessions (clinician role via `X-Role: clinician|researcher|admin`):
  - `POST /clinical/session/start` with `participant_id`, `clinician_id`, `mode`, `session_number`, `goals`.
  - `POST /clinical/session/end` with `session_id`.
- Pre-session snapshot:
  - `GET /clinical/session/{participant_id}/snapshot` → top segments, coherence hint, recent MPG-intuitive trials, recent event count.
- Intervention plans:
  - `POST /clinical/intervention_plan` with `participant_id`, name/type, targets (segment IDs), homework tasks.
- Clinical episodes & notes:
  - `POST /clinical/episode` to create a focused episode (link to segment and/or trial).
  - `POST /clinical/note` to record narrative notes linked to session.
- Protocol templates (CR-107):
  - List/view protocols: `GET /clinical/protocols`, `GET /clinical/protocols/{id}`.
  - Instantiate protocol → InterventionPlan: `POST /clinical/protocols/{id}/instantiate` with `participant_id`.
- Protocol personalization (CR-108 scaffold):
  - List protocol instances: `GET /clinical/protocols/instances`.
  - Get adaptation suggestions: `GET /clinical/adapt/suggestions` (role required).
  - Apply/approve an adaptation: `POST /clinical/adapt/apply` with `protocol_instance_id`, `action`, `target_module_id`, and optional `personalized_weight`.
  - Update module/step scores (feeding adaptation): `POST /clinical/protocols/{instance_id}/scores` with `module_scores` / `step_scores`.
  - Mobile homework from protocols:
    - `GET /mobile/therapy_tasks/{participant_id}?plan_id=...` to fetch plan-specific homework.
    - `GET /mobile/protocol/{instance_id}/plan` to resolve a protocol instance to its plan tasks.
  - Auto-score from plan targets (placeholder): `POST /clinical/protocols/{instance_id}/auto_score` (averages SegmentState coherence/potency over plan targets).

## Neo4j schema additions

Add constraints before first clinical use:

```cypher
CREATE CONSTRAINT clinical_session_id IF NOT EXISTS
FOR (c:ClinicalSession) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT clinical_episode_id IF NOT EXISTS
FOR (e:ClinicalEpisode) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT clinical_note_id IF NOT EXISTS
FOR (n:ClinicalNote) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT intervention_plan_id IF NOT EXISTS
FOR (p:InterventionPlan) REQUIRE p.id IS UNIQUE;
```

Relationships to use:

- `(Participant)-[:HAS_CLINICAL_SESSION]->(ClinicalSession)`
- `(Clinician)-[:CONDUCTS_SESSION]->(ClinicalSession)`
- `(ClinicalSession)-[:HAS_EPISODE]->(ClinicalEpisode)`
- `(ClinicalSession)-[:HAS_NOTE]->(ClinicalNote)`
- `(ClinicalSession)-[:USES_PLAN]->(InterventionPlan)`
- `(InterventionPlan)-[:TARGETS_SEGMENT]->(Segment)`

## Safety and governance reminders

- Guided Mode is **assistive**; all suggestions are hypotheses, not diagnoses or treatment decisions.
- By default, only derived structures (segments, coherence, RV flags) surface; raw email/chat/audio/video content stays hidden.
- Clinicians can hide segments or restrict interventions via participant cockpit/console preferences.

## Frontend wiring pointers

- Clinician console: add a “Clinical” tab that calls snapshot endpoints, shows smoothed somatic/coherence signals, and lists focus segments (use `visible` flag on nodes).
- Participant/KMP app: deliver InterventionPlan homework via existing mobile task flow (`/mobile/experiments`, `/mobile/trial_result`), tagging trials with the relevant plan/session IDs in `payload.segments` or `segments`.
