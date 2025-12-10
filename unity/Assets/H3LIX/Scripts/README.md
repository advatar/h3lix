# H3LIX Unity Scripts (Quest 3 scaffold)

Files under `Assets/H3LIX/` provide:
- `Networking/H3LIXClientConfig.cs` – ScriptableObject with base URL/WS path.
- `Networking/Dto/*.cs` – DTOs matching the FastAPI backend.
- `Networking/H3LIXClient.cs` – HTTP + WebSocket client; enqueues telemetry envelopes.
- `State/H3LIXStore.cs` – Unity MonoBehaviour store; drains the inbound queue each frame and updates MPG graph state.
- `State/InteractionMode.cs`, `PlaybackController.cs` – minimal mode/replay placeholders.
- `Utilities/ThreadDispatcher.cs` – main-thread dispatch helper.

To use:
1) Create a `H3LIXClientConfig` asset (e.g., `Assets/Resources/H3LIXClientConfig.asset`) and set your backend URL (http://<LAN_IP>:8000).
2) Add to your scene:
   - `H3LIXStore` (with config assigned) and `PlaybackController`.
   - `H3LIXBootstrap` to auto-refresh sessions, load the first snapshot, and start streaming.
   - Optional UI: `DashboardBootstrap` (buttons/inputs) and `TimelineController` (slider) if you wire them to Unity UI elements.
   - Visuals: `GraphRenderer` and `CoherenceWallRenderer` to render MPG/coherence using store data.
3) Bind UI/visuals to `H3LIXStore` properties (somatic/symbolic/noetic, MPG graph, rogue/mufs lists, cohorts).
4) Ensure XR settings (OpenXR + Meta) are configured for Quest 3; build as Android ARM64 with Internet permission.

This scaffold is platform-agnostic; configure XR (OpenXR + Meta) and build settings for Quest 3 in Unity. Use the editor menu `H3LIX/Create Sample Scene` to auto-generate a starter scene at `Assets/H3LIX/Scenes/H3LIXSample.unity` and a default config at `Assets/Resources/H3LIXClientConfig.asset`.
