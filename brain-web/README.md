# H3LIX Brain Web Viewer

Minimal 3D client (React + React Three Fiber) for the “minimum viable brain” described in `BRAIN.md`.

## Run locally
1) `cd brain-web`
2) `npm install`
3) `VITE_API_BASE=http://localhost:8000 npm run dev`

The viewer connects to the FastAPI service at `/brain/snapshot` and `/brain/stream`, renders the MPG layout, and shows live stream updates. Use the Participant and Level inputs to filter snapshots, click nodes to inspect, and (if a participant is set) load/play recent history pulled from `/streams/participant/{id}/recent`.
