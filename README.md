# H3LIX / LAIZA Demo Stack (CR-001..CR-010)

Synthetic, reproducible scaffold for the Somatic–Symbolic–Noetic MPG, RV, MUFS, and policy layers.

## Quickstart (local, demo creds)
```
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=neo4j-password
```
Start Neo4j (demo): `docker run -d --name neo4j-h3lix -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/neo4j-password neo4j:5.22`

Run a demo experiment (synthetic placeholder metrics):
```
python experiments/runner.py --config configs/e1_mpg_intuition.yaml
```

Inspect Neo4j for `:Experiment`, `:ExperimentRun`, `:MetricResult`. See `docs/EXPERIMENTS.md` for config mapping and `docs/ETHICS_PRIVACY.md` for guidance. Replace demo credentials for any non-local use.

## Docs
- Architecture overview and Mermaid UML diagrams: `docs/ARCHITECTURE.md`
- Experiments and benchmarks: `docs/EXPERIMENTS.md`, `docs/BENCHMARK_HUB.md`
- Ethics, privacy, and safety: `docs/ETHICS_PRIVACY.md`
- Change requests (requirements backlog): `docs/CR-*.md`

## Apple / visionOS client
- The SwiftUI/RealityKit app lives in `vision/H3LIXVision` (visionOS target). See `APPLE.md` for Apple hardware prerequisites, simulator vs. device notes, and the bring-up plan.
- When running against a local backend, set `H3LIX_BASE_URL=http://127.0.0.1:8000` in the Xcode run scheme. HealthKit streaming requires a provisioned visionOS device with the HealthKit capability enabled.

## Participant cockpit, console, and clinical mode (CR-104–106)

- Participant cockpit APIs:
  - `/participant/{id}/summary`, `/segments/top`, `/segment_feedback`, `/scopes`, `/intervention_prefs`.
- Mobile app APIs:
  - `/mobile/experiments/{id}`, `/mobile/session`, `/mobile/trial_result`.
- Clinician/console (use header `X-Role: clinician|researcher|admin`):
  - `/console/participants/summary`, `/console/mpg/overview`, `/console/experiments`, `/console/policies/op`.
  - Clinical guided mode: `/clinical/session/start`, `/clinical/session/end`, `/clinical/session/{pid}/snapshot`, `/clinical/intervention_plan`.
  - Protocols and personalization: `/clinical/protocols`, `/clinical/protocols/{id}`, `/clinical/protocols/{id}/instantiate`, `/clinical/protocols/instances`, `/clinical/adapt/suggestions`, `/clinical/adapt/apply`.
- Consent and scopes:
  - `/consent/participant` to set allowed scopes (wearables, email, chat, calendar, media, etc.).

See `docs/CLINICAL_MODE.md` for schema constraints and safety notes.

Submit results to the local benchmark hub (after running experiments):
```
python scripts/submit_to_hub.py --team_id demo --arch H3LIX_FULL
```

## Brain viewer (minimum viable)
- API: `uvicorn api.main:app --reload` (uses `/brain/snapshot` + `/brain/stream`). Optional: set `EVENT_STORE_DSN` (Postgres/Timescale) and `ALLOWED_ORIGINS` (comma-separated CORS origins).
- Web client: `cd brain-web && npm install && VITE_API_BASE=http://localhost:8000 npm run dev`.
- Tune `participant_id` and `level` in the UI to filter MPG slices and event tails.

## Visualization API (CR-302 draft)
- Sessions: `GET /v1/sessions`
- Snapshot: `GET /v1/sessions/{session_id}/snapshot`
- MPG subgraph: `GET /v1/sessions/{session_id}/mpg/{level}/subgraph`
- Replay: `GET /v1/sessions/{session_id}/replay?from_ms=0&to_ms=60000`
- Live stream: WebSocket `/v1/stream` with `{"type":"subscribe","session_id":"...", "message_types":["somatic_state", ...]}`; responds with `event` frames.

## Stream/QRV auth
- Set `STREAMS_API_KEY` to require an `X-Api-Key`/`api_key` for `/streams` REST + WebSocket ingestion; `QRV_API_KEY` (or the same `STREAMS_API_KEY`) secures `/qrv` routes.

## Event store (Timescale/Postgres)
- Set `EVENT_STORE_DSN` (and optional `EVENT_STORE_TABLE`) to enable durable storage.
- Initialize the table: `psql "$EVENT_STORE_DSN" -f scripts/event_store_migration.sql` (add `create_hypertable` if using TimescaleDB).
- Ensure the API CORS allowlist matches your viewer origin via `ALLOWED_ORIGINS`.

## Tests
- External pytest plugins (e.g., pytest-vcr + httpx) can break test startup. Use `scripts/run_pytest.sh` (sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`) or run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest`.
