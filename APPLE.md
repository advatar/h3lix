# Apple hardware run plan (Swift)

## Assessment
- The native client lives in `vision/H3LIXVision` as a Swift Package (swift-tools-version 6.2) targeting visionOS. It is built with SwiftUI + RealityKit for the immersive UI, and HealthKit + URLSession/WebSocket for data/streams. No third-party SPM dependencies are declared; only Apple frameworks are linked.
- The app expects a running backend (`api/main.py`, FastAPI) that exposes REST + WebSocket endpoints under `H3LIX_BASE_URL` (default `http://localhost:8000`) and optionally Neo4j/Postgres for richer state.
- HealthKit streaming is supported through `HealthKitStreamer` and pushes samples to `/streams/events` after posting consent. This requires real-device entitlements and user permission; the simulator will not provide HealthKit data.
- An Apple Silicon Mac can run both the backend and the visionOS simulator; a Vision Pro (or future visionOS device) is needed to exercise full immersive/HealthKit capture. The repo also includes an Apple-optimized local LLM hook (`services/llm/local_apple.py`) that can leverage MLX on Apple hardware.

## Prerequisites on Apple hardware
- macOS with Apple Silicon, Xcode 16 (or later toolchain supporting Swift 6.2) and the visionOS 2 SDK installed. Sign in with an Apple Developer account to enable HealthKit and network entitlements.
- Docker (optional) for Neo4j; Postgres/Timescale if you want durable event storage.
- Python 3.10+ with `pip install -r requirements.txt`; optional `pip install mlx-lm` plus `APPLE_LLM_MODEL` for the local MLX LLM.
- If deploying to device: a visionOS provisioned device profile and the HealthKit capability enabled in the app target; add `NSHealthShareUsageDescription`/`NSHealthUpdateUsageDescription` strings and ensure outbound network access is allowed.

## Backend bring-up (macOS)
- Start Neo4j locally (optional but recommended): `docker run -d --name neo4j-h3lix -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/neo4j-password neo4j:5.22`.
- In repo root, create a venv and install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Run the API: `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`. Set env vars as needed: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`; `EVENT_STORE_DSN`/`EVENT_STORE_TABLE` for Postgres; `ALLOWED_ORIGINS` for the visionOS app origin; `LLM_BACKEND_DEFAULT` and `APPLE_LLM_MODEL` if using MLX.
- Validate endpoints quickly: `curl http://localhost:8000/health` and `curl http://localhost:8000/v1/sessions`. The app will fall back to a demo session if none are present.

## Swift/visionOS client bring-up
- Open `vision/H3LIXVision/Package.swift` in Xcode. Schemes include the executable target `H3LIXVision` plus library targets (Core/Net/State/VisualState/Scene/UI) and tests.
- Set the scheme’s run environment to include `H3LIX_BASE_URL` pointing at your backend (e.g., `http://127.0.0.1:8000` when running simulator on the same Mac).
- Capabilities: enable HealthKit (read-only) for the visionOS target if you plan to stream physiological data. RealityKit and network access are already implied; ensure ATS exceptions if you keep HTTP.
- Target selection: pick a visionOS simulator (e.g., “Apple Vision Pro”) for UI/stream testing, or a provisioned device for HealthKit + sensors. ImmersiveSpace requires visionOS; macOS/iOS are not listed in `Package.swift` and would need a platform extension to run outside visionOS.
- Build/test commands (do not run yet): `xcodebuild -scheme H3LIXVision -destination "platform=visionOS Simulator,name=Apple Vision Pro"` or `swift test` within `vision/H3LIXVision` for unit coverage (`H3LIXVisualStateTests`, `H3LIXTeachingTests`).

## Runtime flow to verify
- Launch backend (`uvicorn ...`) and ensure websockets are reachable at `/v1/stream`.
- Run the visionOS app; it will fetch `/v1/sessions` and load a snapshot; if empty, it seeds demo data. Selecting a session can open a WebSocket stream to receive somatic/symbolic/noetic/mpg payloads.
- To push real sensor data, instantiate `HealthKitStreamer` with `participantID` + `sessionID`, call `startStreaming()` after user authorization, and confirm events arrive at the backend (`/streams/events`).
- For teaching/lessons, the app calls `/v1/lessons`, `/v1/cohorts`, etc.; keep those routes enabled in the backend and backed by `ContentStore`.

## Open questions / watchouts
- Swift tools 6.2 and visionOS 2 SDK may still be in beta; align Xcode version accordingly. If constrained to Xcode 15, lower `swift-tools-version` and platform in `Package.swift` before building.
- HealthKit availability on visionOS hardware is evolving; plan fallback telemetry (demo data or synthetic streams) when running on simulator or hardware without sensors.
- If you need macOS/iOS support, add those platforms to `Package.swift`, audit RealityKit usage, and adjust UI layout for non-immersive scenes.
