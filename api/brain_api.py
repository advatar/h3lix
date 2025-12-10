from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from brain.models import BrainEvent, BrainSnapshot
from brain.service import BrainViewService
from streams.bus import StreamBus


def build_brain_router(
    view_service: BrainViewService,
    bus: StreamBus,
) -> APIRouter:
    router = APIRouter(prefix="/brain", tags=["brain"])

    @router.get("/snapshot", response_model=BrainSnapshot)
    def snapshot(
        participant_id: Optional[str] = Query(default=None),
        level: Optional[int] = Query(default=None),
        event_limit: int = Query(default=50, ge=1, le=500),
    ) -> BrainSnapshot:
        return view_service.snapshot(participant_id=participant_id, level=level, event_limit=event_limit)

    @router.websocket("/stream")
    async def brain_stream(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = await bus.subscribe()
        participant_id = websocket.query_params.get("participant_id")
        session_filter = websocket.query_params.get("session_id")
        level_param = websocket.query_params.get("level")
        try:
            level = int(level_param) if level_param is not None and level_param.strip() else None
        except ValueError:
            level = None
        try:
            initial_snapshot = view_service.snapshot(participant_id=participant_id, level=level)
            await websocket.send_json(
                BrainEvent(kind="graph_snapshot", snapshot=initial_snapshot, meta={"initial": True}).model_dump(
                    mode="json"
                )
            )
            while True:
                message = await queue.get()
                meta = message.get("meta", {}) if isinstance(message, dict) else {}
                if participant_id and meta.get("participant_id") and meta.get("participant_id") != participant_id:
                    continue
                if session_filter and meta.get("session_id") and meta.get("session_id") != session_filter:
                    continue
                if isinstance(message, dict) and message.get("kind") in {"qrv_detection", "hild_status"}:
                    await websocket.send_json(
                        BrainEvent(kind="qrv_event", qrv=message, meta=meta).model_dump(mode="json")
                    )
                    continue
                try:
                    event = BrainEvent(**message)
                except Exception:
                    # Skip malformed messages instead of killing the socket.
                    continue
                await websocket.send_json(event.model_dump(mode="json"))
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe(queue)

    return router
