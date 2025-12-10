from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from streams.synthetic import SyntheticTelemetryGenerator


class StartScenarioRequest(BaseModel):
    scenario: str = Field(description="Scenario name defined in SYNT.md, e.g. calm_baseline or rogue_variable_storm")
    participant_id: str = Field(default="demo-user")
    duration_s: Optional[float] = Field(default=None, gt=0.0, description="Override default scenario duration (seconds)")
    interval_ms: Optional[int] = Field(default=None, ge=50, le=5000, description="Override tick interval")
    seed: Optional[int] = Field(default=None, description="Optional deterministic seed")


class StartScenarioResponse(BaseModel):
    run_id: str
    session_id: str
    scenario: str
    expected_messages: int


class TelemetryLogResponse(BaseModel):
    session_id: str
    count: int
    messages: List[dict]


def build_synthetic_router(generator: SyntheticTelemetryGenerator) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["synthetic"])

    @router.get("/synthetic/scenarios")
    def list_scenarios() -> dict:
        return {"scenarios": generator.available_scenarios()}

    @router.post("/sessions/{session_id}/start_scenario", response_model=StartScenarioResponse)
    async def start_scenario(session_id: str, req: StartScenarioRequest) -> StartScenarioResponse:
        try:
            run_id = await generator.start(
                scenario=req.scenario,
                session_id=session_id,
                participant_id=req.participant_id,
                duration_s=req.duration_s,
                interval_ms=req.interval_ms,
                seed=req.seed,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        # approximate message count (somatic + symbolic + noetic per tick)
        config = generator.scenario_config(req.scenario)
        interval = req.interval_ms or config.interval_ms
        duration = req.duration_s or config.duration_s
        ticks = max(1, int((duration * 1000.0) / interval))
        return StartScenarioResponse(
            run_id=run_id,
            session_id=session_id,
            scenario=req.scenario,
            expected_messages=ticks * 3,
        )

    @router.post("/sessions/{session_id}/stop_scenario")
    def stop_scenario(session_id: str) -> dict:
        stopped = generator.stop(session_id)
        return {"session_id": session_id, "stopped": stopped}

    @router.get("/sessions/{session_id}/telemetry", response_model=TelemetryLogResponse)
    def telemetry_log(session_id: str, limit: int = Query(default=500, ge=1, le=5000)) -> TelemetryLogResponse:
        messages = generator.get_log(session_id)
        if not messages:
            raise HTTPException(status_code=404, detail="No synthetic telemetry for session")
        sliced = messages[-limit:]
        return TelemetryLogResponse(
            session_id=session_id,
            count=len(messages),
            messages=[m.model_dump(mode="json") for m in sliced],
        )

    return router
