# H3LIX Quest 3 / Unity Client (Scaffold)

This is a Quest 3–focused Unity scaffold that mirrors the H3LIX Vision app. It includes DTOs, a client, and state stores; you still need to open the project in Unity and finish scene wiring.

## 1) Unity project setup

1) Install **Unity 2022.3 LTS** (or newer) with **Android Build Support**.  
2) Enable **OpenXR** with the **Meta Quest** feature. (Project Settings → XR Plug-in Management.)  
3) Import packages:
   - Meta XR (All-in-One SDK or Oculus Integration) for Quest 3.
   - XR Interaction Toolkit + TextMeshPro.
   - Optional: DOTween for UI polish.
4) Player settings:
   - Min API 29, Target 33+. ARM64 only.
   - Graphics: Vulkan preferred; disable MSAA for perf; URP Forward Renderer.
   - Internet permission on.

## 2) Code scaffold (in `Assets/H3LIX`)

- `Scripts/Networking/H3LIXClient.cs` – HTTP + WebSocket client for the FastAPI backend.
- `Scripts/Networking/Dto/*.cs` – DTOs matching the backend (`SnapshotResponse`, `Mpg*`, symbolic/noetic payloads, Rogue/MUFS).
- `Scripts/State/H3LIXStore.cs` – main state store; drains WebSocket queue on Update.
- `Scripts/State/PlaybackController.cs` – minimal replay cache hook.
- `Scripts/State/InteractionMode.cs` – enum for live/replay/inspect modes.
- `Scripts/Utilities/ThreadDispatcher.cs` – main-thread dispatch helper.
- Streaming/parity: `/v1/*` endpoints, direct (unwrapped) WebSocket payloads, MPG patch deltas, symbolic predictions/uncertainty regions, noetic intuitive accuracy, and richer Rogue/MUFS fields to match the Vision Pro client.
- Sample scene now includes a HUD overlay that surfaces key telemetry values (coherence, intuition estimate, symbolic predictions, rogue/MUFS counts) for quick visual parity checks.

You still need to:
- Create scenes/prefabs for MPG graph, coherence wall, and UI panels.
- Hook `H3LIXStore` into your scene (e.g., via a bootstrap MonoBehaviour).
- Implement layout/visuals per your design.

## 3) Wiring flow

1) Set backend URL/port in `H3LIXClientConfig` ScriptableObject (create an instance in `Assets/Resources/H3LIXClientConfig.asset`).  
2) In the bootstrap MonoBehaviour, construct `H3LIXClient` with the config and create `H3LIXStore`.  
3) On scene start: call `Store.RefreshSessions()`, then `LoadSnapshot(sessionId)`, then `StartStream(sessionId)`.  
4) Subscribe to store events or poll store properties to update UI and visuals each frame.  
5) For replay: call `FetchReplay(sessionId, fromMs, toMs)` on `PlaybackController` and render cached frames.

## 4) Backend endpoints assumed

- `/v1/sessions`, `/v1/sessions/{id}/snapshot`, `/v1/sessions/{id}/replay`
- `/v1/cohorts`, `/v1/cohorts/{id}/noetic-summary`, `/v1/cohorts/{id}/mpg-echoes`
- `/health` (or `/v1/health`), `/mirror/run_trial` (optional), `/clinical/*`, `/mobile/*` if you surface tasks
- `/v1/stream` WebSocket for live telemetry (subscribe payload: `{type:"subscribe", session_id, message_types}`).

## 5) Running locally

Start backend (from repo root):
```
./scripts/start_services.sh 8000
```
Set the Quest device to reach your host IP: in config, use `http://<LAN_IP>:8000`.

## 6) Next steps

- Add a `Dashboard` scene with panels (session picker, controls, telemetry summary, replay scrubber).
- Add MPG graph renderer (instanced spheres + line/tube edges; cap node count for perf).
- Add coherence wall (simple bars/line for group ribbon).
- Add basic error/status banner and reconnection handling.

## Sample scene generator

- In the Unity Editor, use menu: `H3LIX/Create Sample Scene`.
- This creates `Assets/H3LIX/Scenes/H3LIXSample.unity` with:
  - `H3LIXRoot` containing `H3LIXStore`, `PlaybackController`, and `H3LIXBootstrap`.
  - A basic MPG graph renderer and coherence wall placeholders with materials.
  - A `H3LIXClientConfig` asset at `Assets/Resources/H3LIXClientConfig.asset` (set your backend URL).

This scaffold keeps code light; expand DTOs and visuals as you iterate.***
