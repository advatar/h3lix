from __future__ import annotations

import json
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.authz import ensure_role
from api.human_api import db as human_db
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from services.llm import LLMRequest, LLMRouter
from streams.store import InMemoryEventStore, PostgresEventStore


class ExperimentCreate(BaseModel):
    name: str
    template: str
    notes: str | None = None
    prereg_hypothesis: str | None = None
    prereg_metrics: List[str] = Field(default_factory=list)


class PolicyOp(BaseModel):
    policy_id: str
    action: str  # promote | rollback | pause
    rationale: str


class SessionSummaryRequest(BaseModel):
    backend: Optional[str] = Field(default=None, description="LLM backend key (local|remote|auto)")
    max_events: int = Field(default=50, ge=1, le=200)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    system_prompt: Optional[str] = Field(
        default="Summarize the session in 3 concise bullets, focusing on salient events."
    )


def build_console_router(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    event_store: InMemoryEventStore | PostgresEventStore,
    llm_router: Optional[LLMRouter] = None,
) -> APIRouter:
    router = APIRouter(prefix="/console", tags=["console"])

    @router.get("/participants/summary")
    def participants_summary(request: Request) -> Dict:
        ensure_role(request, allowed={"researcher", "clinician", "admin"})
        records = human_db.run("MATCH (p:Participant) RETURN p.id AS id, p.alias AS alias")
        participants = [{"id": r["id"], "alias": r.get("alias", "")} for r in records]
        stream_health = []
        for p in participants:
            latest = event_store.latest(p["id"])
            stream_health.append(
                {
                    "participant_id": p["id"],
                    "last_event": latest.aligned_timestamp.isoformat() if latest else None,
                }
            )
        return {"participants": participants, "stream_health": stream_health}

    @router.get("/mpg/overview")
    def mpg_overview(request: Request) -> Dict:
        ensure_role(request, allowed={"researcher", "clinician", "admin"})
        graph = repo.get_graph()
        total_nodes = graph.number_of_nodes()
        total_edges = graph.number_of_edges()
        segments = [
            (node, data) for node, data in graph.nodes(data=True) if "Segment" in data.get("labels", []) or data.get("level", 0) >= 1
        ]
        importances = [float(d.get("importance", 0.0)) for _, d in segments]
        confidences = [float(d.get("confidence", 0.0)) for _, d in segments]
        return {
            "nodes": total_nodes,
            "edges": total_edges,
            "segments": len(segments),
            "importance_mean": (sum(importances) / len(importances)) if importances else 0.0,
            "confidence_mean": (sum(confidences) / len(confidences)) if confidences else 0.0,
        }

    @router.get("/experiments")
    def list_experiments(request: Request) -> List[Dict]:
        ensure_role(request, allowed={"researcher", "admin"})
        recs = human_db.run("MATCH (e:Experiment) RETURN e ORDER BY e.created_at DESC")
        return [dict(r["e"]) for r in recs]

    @router.post("/experiments")
    def create_experiment(request: Request, body: ExperimentCreate) -> Dict:
        ensure_role(request, allowed={"researcher", "admin"})
        result = human_db.run(
            """
            CREATE (e:Experiment {
                id: randomUUID(),
                name: $name,
                template: $template,
                notes: coalesce($notes, ""),
                prereg_hypothesis: coalesce($hypothesis, ""),
                prereg_metrics: $metrics,
                created_at: datetime()
            })
            RETURN e
            """,
            name=body.name,
            template=body.template,
            notes=body.notes,
            hypothesis=body.prereg_hypothesis,
            metrics=body.prereg_metrics,
        )
        record = result[0] if result else None
        if not record:
            raise HTTPException(status_code=500, detail="Failed to create experiment")
        return dict(record["e"])

    @router.post("/policies/op")
    def policy_operation(request: Request, body: PolicyOp) -> Dict:
        ensure_role(request, allowed={"admin", "researcher"})
        # Log-only stub; integrate with policy engine in CR-007/008
        return {
            "status": "logged",
            "policy_id": body.policy_id,
            "action": body.action,
            "rationale": body.rationale,
        }

    @router.post("/sessions/{session_id}/summary")
    def session_summary(request: Request, session_id: str, body: SessionSummaryRequest) -> Dict:
        ensure_role(request, allowed={"researcher", "clinician", "admin"})
        records = [r for r in event_store.all_records() if getattr(r.event, "session_id", None) == session_id]
        if not records:
            raise HTTPException(status_code=404, detail="Session not found or no events")
        records = sorted(records, key=lambda r: r.aligned_timestamp)[-body.max_events :]
        lines: List[str] = []
        for rec in records:
            ts = rec.aligned_timestamp.isoformat()
            payload = rec.event.payload
            snippet = ""
            if isinstance(payload, dict) and payload:
                snippet = json.dumps({k: payload[k] for k in list(payload.keys())[:3]}, default=str)
            lines.append(f"[{ts}] {rec.event.stream_type} from {rec.event.source}: {snippet}")
        prompt = (
            f"Session ID: {session_id}\n"
            f"Latest {len(records)} events:\n"
            + "\n".join(lines)
        )

        if llm_router and llm_router.clients:
            llm_req = LLMRequest(
                prompt=prompt,
                system_prompt=body.system_prompt,
                max_tokens=256,
                temperature=body.temperature,
            )
            try:
                llm_resp, backend_used = llm_router.generate(llm_req, backend=body.backend)
                summary_text = llm_resp.text
            except Exception as exc:
                backend_used = body.backend or llm_router.default_backend or "unconfigured"
                summary_text = f"[LLM unavailable: {exc}]"
        else:
            backend_used = "none"
            summary_text = "LLM router not configured; no summary generated."

        return {
            "session_id": session_id,
            "backend": backend_used,
            "events_used": len(records),
            "summary": summary_text,
        }

    return router
