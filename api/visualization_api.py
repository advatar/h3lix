from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Optional, Set
import uuid

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from schemas.api import (
    DecisionTraceResponse,
    MpgSubgraphResponse,
    ReplayResponse,
    SessionSummary,
    SnapshotMpg,
    SnapshotResponse,
)
from schemas.telemetry import (
    MessageType,
    MpgEdge,
    MpgNode,
    MpgSegment,
    NoeticStatePayload,
    SomaticStatePayload,
    SymbolicStatePayload,
    TelemetryEnvelope,
)
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from streams.bus import StreamBus
from streams.models import EventRecord
from streams.store import InMemoryEventStore, PostgresEventStore
from streams.synthetic import SyntheticTelemetryGenerator


def _iso(ts: datetime) -> str:
    return ts.isoformat()


def _infer_session_id(record: EventRecord) -> Optional[str]:
    return record.event.session_id or record.event.payload.get("session_id")


def _collect_sessions(records: List[EventRecord]) -> List[SessionSummary]:
    sessions: Dict[str, Dict[str, str]] = {}
    for rec in records:
        sid = _infer_session_id(rec)
        if not sid:
            continue
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "experiment_id": rec.event.payload.get("experiment_id", "unknown"),
                "subject_id": rec.event.participant_id,
                "status": "active",
                "started_utc": _iso(rec.aligned_timestamp),
                "ended_utc": None,
            }
        sessions[sid]["ended_utc"] = _iso(rec.aligned_timestamp)
    return [SessionSummary(**data) for data in sessions.values()]


def _message_type_from_stream(stream_type: str) -> str:
    if stream_type == "somatic":
        return "somatic_state"
    if stream_type in {"text", "audio", "video"}:
        return "symbolic_state"
    return "noetic_state"


def _envelope_from_record(rec: EventRecord, sequence: int) -> TelemetryEnvelope:
    payload = rec.event.payload or {}
    session_id = _infer_session_id(rec) or "session_default"
    msg_type_raw = _message_type_from_stream(
        rec.event.stream_type.value if hasattr(rec.event.stream_type, "value") else str(rec.event.stream_type)
    )
    msg_type = MessageType(msg_type_raw) if msg_type_raw in MessageType._value2member_map_ else MessageType.SOMATIC_STATE
    return TelemetryEnvelope(
        message_type=msg_type,
        timestamp_utc=_iso(rec.aligned_timestamp),
        experiment_id=payload.get("experiment_id", "unknown"),
        session_id=session_id,
        subject_id=rec.event.participant_id,
        run_id=payload.get("run_id"),
        source_layer="Somatic" if msg_type == MessageType.SOMATIC_STATE else "Symbolic",
        sequence=sequence,
        payload=payload,
    )


def _latest_by_type(records: List[EventRecord]) -> Dict[str, EventRecord]:
    latest: Dict[str, EventRecord] = {}
    for rec in records:
        mt = _message_type_from_stream(rec.event.stream_type.value if hasattr(rec.event.stream_type, "value") else str(rec.event.stream_type))
        if mt not in latest or latest[mt].aligned_timestamp < rec.aligned_timestamp:
            latest[mt] = rec
    return latest


def build_visualization_router(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    event_store: InMemoryEventStore | PostgresEventStore,
    bus: StreamBus,
    synthetic: Optional[SyntheticTelemetryGenerator] = None,
    qrv_manager: Optional["QRVManager"] = None,
) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["visualization"])

    @router.get("/sessions")
    def list_sessions() -> List[SessionSummary]:
        return _collect_sessions(list(event_store.all_records()))

    @router.get("/sessions/{session_id}/snapshot", response_model=SnapshotResponse)
    def session_snapshot(session_id: str, t_rel_ms: Optional[int] = Query(default=None)) -> SnapshotResponse:
        records = [r for r in event_store.all_records() if _infer_session_id(r) == session_id]
        if not records:
            raise HTTPException(status_code=404, detail="Session not found")
        latest = _latest_by_type(records)
        somatic_rec = latest.get("somatic_state")
        symbolic_rec = latest.get("symbolic_state")
        noetic_rec = latest.get("noetic_state")
        default_somatic = {"t_rel_ms": t_rel_ms or 0, "window_ms": 0, "features": {}}
        default_symbolic = {"t_rel_ms": t_rel_ms or 0, "belief_revision_id": "br0", "beliefs": [], "predictions": [], "uncertainty_regions": []}
        default_noetic = {
            "t_rel_ms": t_rel_ms or 0,
            "window_ms": 0,
            "global_coherence_score": 0.0,
            "entropy_change": 0.0,
            "stream_correlations": [],
            "coherence_spectrum": [],
        }
        somatic_payload = (somatic_rec.event.payload if somatic_rec else {}) | default_somatic
        symbolic_payload = (symbolic_rec.event.payload if symbolic_rec else {}) | default_symbolic
        noetic_payload = (noetic_rec.event.payload if noetic_rec else {}) | default_noetic
        somatic = SomaticStatePayload(**somatic_payload)
        symbolic = SymbolicStatePayload(**symbolic_payload)
        noetic = NoeticStatePayload(**noetic_payload)
        graph = repo.get_graph(level=None)
        nodes = []
        edges = []
        segments = []
        for nid, data in graph.nodes(data=True):
            nodes.append(
                MpgNode(
                    id=str(nid),
                    label=str(data.get("name") or nid),
                    description=data.get("reasoning"),
                    layer_tags=[str(l) for l in data.get("layers", [])],
                    metrics={
                        "valence": float(data.get("valence", 0.0) or 0.0),
                        "intensity": float(data.get("intensity", 0.0) or 0.0),
                        "recency": float(data.get("recency", 0.0) or 0.0),
                        "stability": float(data.get("stability", 0.0) or 0.0),
                    },
                    confidence=float(data.get("confidence", 0.0) or 0.0),
                    importance=float(data.get("importance", 0.0) or 0.0),
                    roles=data.get("labels", []),
                    reasoning_provenance=data.get("reasoning"),
                )
            )
            if "Segment" in data.get("labels", []) or data.get("level", 0) >= 1:
                segments.append(
                    MpgSegment(
                        id=str(nid),
                        label=str(data.get("name") or nid),
                        level=int(data.get("level", 0) or 0),
                        member_node_ids=[],
                        cohesion=float(data.get("stability", 0.0) or 0.0),
                        average_importance=float(data.get("importance", 0.0) or 0.0),
                        average_confidence=float(data.get("confidence", 0.0) or 0.0),
                        affective_load=float(data.get("intensity", 0.0) or 0.0),
                    )
                )
        for src, dst, data in graph.edges(data=True):
            edges.append(
                MpgEdge(
                    id=f"{src}->{dst}",
                    source=str(src),
                    target=str(dst),
                    type=str(data.get("rel_type") or data.get("type") or "related"),
                    strength=float(data.get("strength", 0.0) or 0.0),
                    confidence=float(data.get("confidence", 0.0) or 0.0),
                )
            )
        base_subgraph = MpgSubgraphResponse(
            mpg_id="mpg_default", level=0, nodes=nodes[:500], edges=edges[:1000], segments=segments[:100]
        )
        level_summary = [ {"level": 0, "node_count": len(nodes), "segment_count": len(segments)} ]
        return SnapshotResponse(
            session_id=session_id,
            t_rel_ms=t_rel_ms or 0,
            somatic=somatic,
            symbolic=symbolic,
            noetic=noetic,
            last_decision_cycle=None,
            mpg=SnapshotMpg(mpg_id="mpg_default", level_summaries=level_summary, base_subgraph=base_subgraph),
        )

    @router.get("/sessions/{session_id}/qrv_events")
    def qrv_events(session_id: str) -> Dict:
        if not qrv_manager:
            raise HTTPException(status_code=503, detail="QRV manager unavailable")
        return qrv_manager.list_events(session_id=session_id)

    @router.get("/sessions/{session_id}/mpg/{level}/subgraph", response_model=MpgSubgraphResponse)
    def mpg_subgraph(session_id: str, level: int, center_node_id: Optional[str] = None, radius: int = 1, max_nodes: int = 500) -> MpgSubgraphResponse:
        graph = repo.get_graph(level=level)
        if center_node_id and center_node_id not in graph:
            raise HTTPException(status_code=404, detail="center_node_id not found")
        nodes: List[MpgNode] = []
        edges: List[MpgEdge] = []
        segments: List[MpgSegment] = []
        selected_nodes: Set[str] = set(graph.nodes()) if not center_node_id else set()
        if center_node_id:
            selected_nodes.add(center_node_id)
            for _ in range(radius):
                neighbors = set()
                for nid in selected_nodes:
                    neighbors.update(graph.predecessors(nid))
                    neighbors.update(graph.successors(nid))
                selected_nodes.update(neighbors)
        for nid, data in graph.nodes(data=True):
            if selected_nodes and nid not in selected_nodes:
                continue
            if len(nodes) >= max_nodes:
                break
            nodes.append(
                MpgNode(
                    id=str(nid),
                    label=str(data.get("name") or nid),
                    layer_tags=[str(l) for l in data.get("layers", [])],
                    metrics={
                        "valence": float(data.get("valence", 0.0) or 0.0),
                        "intensity": float(data.get("intensity", 0.0) or 0.0),
                        "recency": float(data.get("recency", 0.0) or 0.0),
                        "stability": float(data.get("stability", 0.0) or 0.0),
                    },
                    confidence=float(data.get("confidence", 0.0) or 0.0),
                    importance=float(data.get("importance", 0.0) or 0.0),
                    roles=data.get("labels", []),
                )
            )
        node_set = {n.id for n in nodes}
        for src, dst, data in graph.edges(data=True):
            if node_set and src not in node_set or dst not in node_set:
                continue
            edges.append(
                MpgEdge(
                    id=f"{src}->{dst}",
                    source=str(src),
                    target=str(dst),
                    type=str(data.get("rel_type") or data.get("type") or "related"),
                    strength=float(data.get("strength", 0.0) or 0.0),
                    confidence=float(data.get("confidence", 0.0) or 0.0),
                )
            )
        return MpgSubgraphResponse(
            mpg_id="mpg_default",
            level=level,
            center_node_id=center_node_id,
            nodes=nodes,
            edges=edges,
            segments=segments,
        )

    @router.get("/sessions/{session_id}/decisions/{decision_id}", response_model=DecisionTraceResponse)
    def decision_trace(session_id: str, decision_id: str) -> DecisionTraceResponse:
        return DecisionTraceResponse(session_id=session_id, decision_id=decision_id, phases=[])

    @router.get("/sessions/{session_id}/replay", response_model=ReplayResponse)
    def replay(
        session_id: str,
        from_ms: int = Query(default=0, ge=0),
        to_ms: int = Query(default=60000, ge=0),
        message_types: Optional[str] = Query(default=None),
        max_messages: int = Query(default=5000, ge=1, le=20000),
    ) -> ReplayResponse:
        records = [r for r in event_store.all_records() if _infer_session_id(r) == session_id]
        synthetic_msgs = synthetic.get_log(session_id) if synthetic else []
        if not records and not synthetic_msgs:
            raise HTTPException(status_code=404, detail="Session not found")
        start_candidates = []
        if records:
            start_candidates.append(min(r.aligned_timestamp for r in records))
        if synthetic_msgs:
            try:
                start_candidates.append(min(e.timestamp_utc for e in synthetic_msgs))
            except Exception:
                pass
        start_ts = min(start_candidates) if start_candidates else datetime.utcnow()
        allowed_types = None
        if message_types:
            allowed_types = {mt.strip() for mt in message_types.split(",") if mt.strip()}
        envelopes: List[TelemetryEnvelope] = []
        if records:
            for rec in sorted(records, key=lambda r: r.aligned_timestamp):
                t_rel = int((rec.aligned_timestamp - start_ts).total_seconds() * 1000)
                env = _envelope_from_record(rec, sequence=0)
                try:
                    env.payload["t_rel_ms"] = t_rel
                except Exception:
                    pass
                envelopes.append(env)
        if synthetic_msgs:
            for env in synthetic_msgs:
                env_copy = env.model_copy(deep=True)
                if isinstance(env_copy.timestamp_utc, str):
                    try:
                        env_copy.timestamp_utc = datetime.fromisoformat(env_copy.timestamp_utc.replace("Z", "+00:00"))
                    except Exception:
                        env_copy.timestamp_utc = datetime.utcnow()
                t_rel = int((env_copy.timestamp_utc - start_ts).total_seconds() * 1000)
                if hasattr(env_copy.payload, "t_rel_ms"):
                    try:
                        env_copy.payload.t_rel_ms = t_rel
                    except Exception:
                        pass
                envelopes.append(env_copy)
        envelopes.sort(key=lambda e: (e.timestamp_utc, getattr(e, "sequence", 0)))
        filtered: List[TelemetryEnvelope] = []
        for idx, env in enumerate(envelopes):
            t_rel = None
            payload = env.payload
            if isinstance(payload, dict):
                t_rel = payload.get("t_rel_ms")
            elif hasattr(payload, "t_rel_ms"):
                t_rel = getattr(payload, "t_rel_ms", None)
            if t_rel is None and isinstance(env.timestamp_utc, datetime):
                t_rel = int((env.timestamp_utc - start_ts).total_seconds() * 1000)
            if t_rel is None:
                t_rel = 0
            if t_rel < from_ms or t_rel > to_ms:
                continue
            if allowed_types and env.message_type.value not in allowed_types:
                continue
            env.sequence = idx
            if isinstance(payload, dict):
                payload["t_rel_ms"] = t_rel
            elif hasattr(payload, "t_rel_ms"):
                try:
                    payload.t_rel_ms = t_rel
                except Exception:
                    pass
            filtered.append(env)
            if len(filtered) >= max_messages:
                break
        return ReplayResponse(session_id=session_id, from_ms=from_ms, to_ms=to_ms, messages=filtered)

    @router.get("/stream")
    def stream_info() -> dict:
        return {
            "detail": "WebSocket endpoint available",
            "connect": "/v1/stream",
            "protocol": "websocket",
            "subprotocol": "json_v1",
            "subscribe_example": {"type": "subscribe", "session_id": "session_default", "message_types": ["somatic_state"]},
        }

    @router.websocket("/stream")
    async def stream(websocket: WebSocket) -> None:
        await websocket.accept(subprotocol="json_v1")
        queue = await bus.subscribe()
        subscription_id = str(uuid.uuid4())
        session_filter: Optional[str] = None
        type_filter: Optional[Set[str]] = None
        try:
            msg = await websocket.receive_text()
            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                return
            if payload.get("type") != "subscribe":
                await websocket.send_json({"type": "error", "detail": "Expected subscribe message"})
                return
            session_filter = payload.get("session_id")
            mtypes = payload.get("message_types") or []
            if mtypes:
                type_filter = {str(mt) for mt in mtypes}
            await websocket.send_json({"type": "ack", "subscription_id": subscription_id})
            while True:
                message = await queue.get()
                meta = message.get("meta", {}) if isinstance(message, dict) else {}
                telemetry_payload = message.get("telemetry") if isinstance(message, dict) else None
                if telemetry_payload is not None:
                    try:
                        env = telemetry_payload if isinstance(telemetry_payload, TelemetryEnvelope) else TelemetryEnvelope(**telemetry_payload)
                    except Exception:
                        continue
                    if session_filter and env.session_id != session_filter:
                        continue
                    if type_filter and env.message_type.value not in type_filter:
                        continue
                    await websocket.send_json({"type": "event", "subscription_id": subscription_id, "data": env.model_dump(mode="json")})
                    continue
                if session_filter and meta.get("session_id") and meta.get("session_id") != session_filter:
                    continue
                mt = meta.get("message_type") or meta.get("stream_type")
                if type_filter and mt not in type_filter:
                    continue
                stream_payload = message.get("stream", {}) if isinstance(message, dict) else {}
                receipt = stream_payload.get("receipt", {}) if isinstance(stream_payload, dict) else {}
                ts_ms = meta.get("aligned_ts_ms") or stream_payload.get("aligned_ts_ms")
                ts_iso = receipt.get("aligned_timestamp")
                if not ts_iso and ts_ms:
                    ts_iso = datetime.utcfromtimestamp(float(ts_ms) / 1000.0).isoformat() + "Z"
                msg_type = MessageType(mt) if mt in MessageType._value2member_map_ else MessageType.SOMATIC_STATE
                metrics = stream_payload.get("metrics", {}) if isinstance(stream_payload, dict) else {}
                t_rel = int(ts_ms) if ts_ms is not None else 0
                if msg_type == MessageType.SOMATIC_STATE:
                    payload_data = {"t_rel_ms": t_rel, "window_ms": 0, "features": metrics}
                elif msg_type == MessageType.SYMBOLIC_STATE:
                    payload_data = {
                        "t_rel_ms": t_rel,
                        "belief_revision_id": "sim_br0",
                        "beliefs": [],
                        "predictions": [],
                        "uncertainty_regions": [],
                    }
                elif msg_type == MessageType.NOETIC_STATE:
                    payload_data = {
                        "t_rel_ms": t_rel,
                        "window_ms": 0,
                        "global_coherence_score": float(metrics.get("noetic_coherence", 0.0)) if isinstance(metrics, dict) else 0.0,
                        "entropy_change": 0.0,
                        "stream_correlations": [],
                        "coherence_spectrum": [],
                    }
                else:
                    payload_data = {"t_rel_ms": t_rel, "window_ms": 0, "features": metrics}
                envelope = TelemetryEnvelope(
                    message_type=msg_type,
                    timestamp_utc=ts_iso or datetime.utcnow().isoformat() + "Z",
                    experiment_id=meta.get("experiment_id", "unknown"),
                    session_id=meta.get("session_id", "session_default"),
                    subject_id=receipt.get("participant_id", "unknown"),
                    source_layer="Somatic" if msg_type == MessageType.SOMATIC_STATE else "Symbolic",
                    sequence=int(meta.get("sequence", 0) or 0),
                    payload=payload_data,
                )
                await websocket.send_json({"type": "event", "subscription_id": subscription_id, "data": envelope.model_dump(mode="json")})
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe(queue)

    return router
