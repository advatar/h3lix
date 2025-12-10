from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from streams.bus import StreamBus
from services.llm.base import LLMRequest
from services.llm.remote_vllm import RemoteVLLMClient, RemoteVLLMConfig

router = APIRouter(prefix="/afm", tags=["afm"])

# Shared in-process bus for AFM requests going to clients
afm_bus = StreamBus()
_pending: Dict[str, asyncio.Future] = {}
_pending_lock = asyncio.Lock()

_client_health: Dict[str, Tuple[float, Dict[str, object]]] = {}
_health_lock = asyncio.Lock()
_health_ttl_s = 30.0
_max_pending = 8  # cap concurrent AFM requests to avoid overloading the headset

# Optional remote fallback client (e.g., vLLM on Spark)
try:
    _remote_client = RemoteVLLMClient(RemoteVLLMConfig())
except Exception:
    _remote_client = None


class AFMGenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=256, ge=1, le=2048)
    stop: Optional[List[str]] = None
    session_id: Optional[str] = None
    timeout_s: float = Field(default=30.0, ge=1.0, le=120.0)
    prefer: str = Field(default="auto", description="auto|native|remote; auto uses healthy AFM else remote fallback")


class AFMGenerateResponse(BaseModel):
    request_id: str
    text: str
    model: Optional[str] = None
    backend: str = "native"
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


@router.post("/request", response_model=AFMGenerateResponse)
async def afm_request(body: AFMGenerateRequest) -> AFMGenerateResponse:
    # Prefer native AFM if healthy client available; otherwise fallback to remote if configured.
    use_native = body.prefer in {"auto", "native"} and await _has_healthy_client()
    if not use_native and body.prefer == "native":
        raise HTTPException(status_code=503, detail="No healthy AFM client available")
    if not use_native and body.prefer in {"auto", "remote"}:
        if _remote_client is None:
            raise HTTPException(status_code=503, detail="Remote LLM not configured")
        try:
            resp = _remote_client.generate(
                LLMRequest(
                    prompt=body.prompt,
                    max_tokens=body.max_tokens,
                    temperature=body.temperature,
                    system_prompt=None,
                    stop=body.stop,
                )
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Remote LLM failed: {exc}")
        return AFMGenerateResponse(
            request_id="remote-" + str(uuid.uuid4()),
            text=resp.text,
            model=resp.model,
            backend="remote",
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
        )

    async with _pending_lock:
        if len(_pending) >= _max_pending:
            raise HTTPException(status_code=429, detail="Too many AFM requests in flight")

    request_id = str(uuid.uuid4())
    message = {
        "type": "afm_request",
        "request_id": request_id,
        "model": body.model or "native",
        "prompt": body.prompt,
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
        "stop": body.stop or [],
        "session_id": body.session_id,
    }
    fut: asyncio.Future = asyncio.get_running_loop().create_future()
    async with _pending_lock:
        _pending[request_id] = fut
    await afm_bus.publish(message)
    try:
        result = await asyncio.wait_for(fut, timeout=body.timeout_s)
    except asyncio.TimeoutError:
        async with _pending_lock:
            _pending.pop(request_id, None)
        raise HTTPException(status_code=504, detail="AFM client did not respond in time")
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="Invalid AFM response")
    return AFMGenerateResponse(
        request_id=request_id,
        text=str(result.get("text", "")),
        model=result.get("model"),
        backend="native",
        prompt_tokens=result.get("prompt_tokens"),
        completion_tokens=result.get("completion_tokens"),
    )


async def _send_loop(websocket: WebSocket, queue: asyncio.Queue) -> None:
    while True:
        message = await queue.get()
        await websocket.send_json(message)


async def _has_healthy_client() -> bool:
    cutoff = time.time() - _health_ttl_s
    async with _health_lock:
        for _, (ts, health) in list(_client_health.items()):
            if ts < cutoff:
                continue
            busy = bool(health.get("busy", False))
            fps = float(health.get("fps", 60.0) or 0.0)
            thermal = str(health.get("thermal", "")).lower()
            if busy:
                continue
            if fps < 50.0:
                continue
            if thermal in {"hot", "critical"}:
                continue
            return True
    return False


@router.websocket("/bridge")
async def afm_bridge(websocket: WebSocket) -> None:
    await websocket.accept(subprotocol="json_v1")
    queue = await afm_bus.subscribe()
    send_task = asyncio.create_task(_send_loop(websocket, queue))
    client_id = str(uuid.uuid4())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue
            msg_type = payload.get("type")
            if msg_type == "register":
                if payload.get("client_id"):
                    client_id = str(payload["client_id"])
                await websocket.send_json({"type": "ack", "role": "afm_client", "client_id": client_id})
            elif msg_type == "health":
                async with _health_lock:
                    _client_health[client_id] = (
                        time.time(),
                        {
                            "fps": payload.get("fps"),
                            "thermal": payload.get("thermal"),
                            "busy": payload.get("busy"),
                        },
                    )
            elif msg_type == "afm_result":
                request_id = payload.get("request_id")
                async with _pending_lock:
                    fut = _pending.pop(request_id, None)
                if fut and not fut.done():
                    fut.set_result(payload)
            elif msg_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat_ack"})
            else:
                await websocket.send_json({"type": "error", "detail": "Unknown message type"})
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
        afm_bus.unsubscribe(queue)
        async with _health_lock:
            _client_health.pop(client_id, None)
