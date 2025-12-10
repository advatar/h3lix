from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from core.qrv.manager import QRVManager
from api.authz import ensure_role


class SnapshotRequest(BaseModel):
    session_id: str
    t_rel_ms: float = 0.0
    feature_overrides: List[float] = Field(default_factory=list)


class HILDAckRequest(BaseModel):
    session_id: str
    response: str
    t_rel_ms: float = 0.0


def build_qrv_router(manager: QRVManager) -> APIRouter:
    router = APIRouter(prefix="/qrv", tags=["qrvm"])
    api_key = os.getenv("QRV_API_KEY") or os.getenv("STREAMS_API_KEY")

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

    @router.post("/snapshot")
    def snapshot(req: SnapshotRequest, request: Request) -> dict:
        _require_api_key(request)
        return manager.process_tick(
            session_id=req.session_id,
            t_rel_ms=req.t_rel_ms,
            feature_overrides=req.feature_overrides,
        )

    @router.post("/hild/ack")
    def acknowledge(request: Request, req: HILDAckRequest) -> dict:
        _require_api_key(request)
        ensure_role(request, allowed={"clinician", "director", "researcher", "admin"})
        status = manager.acknowledge_prompt(req.session_id, req.response, req.t_rel_ms)
        return status.model_dump()

    @router.get("/events")
    def events(request: Request, session_id: Optional[str] = None) -> dict:
        _require_api_key(request)
        return manager.list_events(session_id=session_id)

    @router.get("/status/{session_id}")
    def status(session_id: str, request: Request) -> dict:
        _require_api_key(request)
        return manager.status(session_id=session_id).model_dump()

    @router.websocket("/stream")
    async def qrv_stream(websocket: WebSocket) -> None:
        await websocket.accept()
        if not await _require_ws_api_key(websocket):
            return
        session_filter = websocket.query_params.get("session_id")
        bus = manager.bus
        if not bus:
            await websocket.send_json({"type": "error", "detail": "bus unavailable"})
            await websocket.close()
            return
        queue = await bus.subscribe()
        try:
            while True:
                message = await queue.get()
                if not isinstance(message, dict):
                    continue
                kind = message.get("kind")
                if kind not in {"qrv_detection", "hild_status"}:
                    continue
                if session_filter and message.get("session_id") != session_filter:
                    continue
                await websocket.send_json(message)
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe(queue)

    return router
