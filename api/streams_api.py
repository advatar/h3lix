from __future__ import annotations

import asyncio
import json
import random
import os
from datetime import datetime, timezone
from typing import List, Optional, Set

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from streams.ingest import EventIngestService
from streams.consent import STREAM_SCOPE_MAP
from streams.models import BatchIngestResponse, EventBatch, EventEnvelope, EventReceipt, EventRecord, StreamType


class SimulationRequest(BaseModel):
    session_id: str = "sim-session"
    participant_id: str = "sim-user"
    count: int = Field(default=20, ge=1, le=10000)
    interval_ms: int = Field(default=500, ge=10, le=60000)
    seed: Optional[int] = None


def _fake_somatic_payload(rng: random.Random, seq: int) -> dict:
    hr = 70.0 + rng.uniform(-3, 3) + 0.05 * seq
    eda = 0.2 + rng.uniform(-0.05, 0.05) + 0.001 * seq
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "trial_id": "sim-trial",
        "samples": [
            {"channel": "hr", "value": hr, "timestamp_utc": now_iso},
            {"channel": "eda", "value": eda, "timestamp_utc": now_iso},
        ],
    }


def build_streams_router(ingest_service: EventIngestService) -> APIRouter:
    router = APIRouter(prefix="/streams", tags=["streams"])
    simulation_tasks: Set[asyncio.Task] = set()
    api_key = os.getenv("STREAMS_API_KEY")

    def _require_api_key(request: Request) -> None:
        if not api_key:
            return
        provided = request.headers.get("x-api-key")
        if provided != api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    async def _require_ws_api_key(websocket: WebSocket) -> bool:
        if not api_key:
            return True
        provided = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
        if provided != api_key:
            await websocket.close(code=4401)
            return False
        return True

    @router.post("/event", response_model=EventReceipt)
    async def ingest_event(event: EventEnvelope, request: Request) -> EventReceipt:
        _require_api_key(request)
        try:
            record = await ingest_service.ingest(event)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        return EventReceipt.from_record(record)

    @router.post("/events", response_model=BatchIngestResponse)
    async def ingest_events(batch: EventBatch, request: Request) -> BatchIngestResponse:
        _require_api_key(request)
        try:
            records = await ingest_service.ingest_batch(batch)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        return ingest_service.to_batch_response(records)

    @router.get("/participant/{participant_id}/recent", response_model=List[EventRecord])
    def recent_events(
        request: Request,
        participant_id: str,
        stream_type: Optional[StreamType] = Query(default=None),
        limit: int = Query(default=25, ge=1, le=500),
    ) -> List[EventRecord]:
        _require_api_key(request)
        records = ingest_service.store.list(participant_id, stream_type=stream_type, limit=limit)
        if not records:
            raise HTTPException(status_code=404, detail="No events found")
        return records

    @router.post("/simulate")
    async def simulate(req: SimulationRequest, request: Request) -> dict:
        _require_api_key(request)
        rng = random.Random(req.seed or int(datetime.now(tz=timezone.utc).timestamp() * 1000))
        scope = STREAM_SCOPE_MAP.get(StreamType.somatic, "wearables")
        if getattr(ingest_service, "consent_manager", None):
            ingest_service.consent_manager.set_scopes(req.participant_id, [scope])

        async def _run_simulation() -> None:
            for idx in range(req.count):
                event = EventEnvelope(
                    participant_id=req.participant_id,
                    source="simulator",
                    stream_type=StreamType.somatic,
                    timestamp_utc=datetime.now(timezone.utc),
                    session_id=req.session_id,
                    payload=_fake_somatic_payload(rng, idx),
                )
                await ingest_service.ingest(event)
                if idx < req.count - 1:
                    await asyncio.sleep(req.interval_ms / 1000.0)

        task = asyncio.create_task(_run_simulation())
        simulation_tasks.add(task)
        task.add_done_callback(simulation_tasks.discard)
        return {"status": "started", "session_id": req.session_id, "participant_id": req.participant_id, "events": req.count}

    @router.websocket("/ingest")
    async def ingest_websocket(websocket: WebSocket) -> None:
        """Ingest EventEnvelope payloads over a persistent websocket."""
        await websocket.accept(subprotocol="json_v1")
        if not await _require_ws_api_key(websocket):
            return
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                    continue

                # Accept either a single EventEnvelope or a batch: {"events": [...]}
                if isinstance(payload, dict) and "events" in payload:
                    try:
                        batch = EventBatch.model_validate(payload)
                    except Exception as exc:
                        await websocket.send_json({"type": "error", "detail": f"Invalid batch: {exc}"})
                        continue
                    try:
                        records = await ingest_service.ingest_batch(batch)
                    except PermissionError as exc:
                        await websocket.send_json({"type": "error", "detail": str(exc)})
                        continue
                    await websocket.send_json(
                        {
                            "type": "ack",
                            "count": len(records),
                            "ingested": [rec.event.event_id for rec in records],
                        }
                    )
                else:
                    try:
                        event = EventEnvelope.model_validate(payload)
                    except Exception as exc:
                        await websocket.send_json({"type": "error", "detail": f"Invalid event: {exc}"})
                        continue
                    try:
                        record = await ingest_service.ingest(event)
                    except PermissionError as exc:
                        await websocket.send_json({"type": "error", "detail": str(exc)})
                        continue
                    await websocket.send_json(
                        {
                            "type": "ack",
                            "event_id": event.event_id,
                            "participant_id": event.participant_id,
                            "stream_type": event.stream_type.value,
                            "aligned_ts_ms": int(record.aligned_timestamp.timestamp() * 1000),
                        }
                    )
        except WebSocketDisconnect:
            pass

    return router
