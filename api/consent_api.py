from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from streams.consent import ConsentManager


class ConsentUpdate(BaseModel):
    participant_id: str
    scopes: List[str] = Field(default_factory=list)


def build_consent_router(consent_manager: ConsentManager) -> APIRouter:
    router = APIRouter(prefix="/consent", tags=["consent"])

    @router.post("/participant")
    def set_consent(update: ConsentUpdate) -> dict:
        consent_manager.set_scopes(update.participant_id, update.scopes)
        return {"status": "ok", "participant_id": update.participant_id, "scopes": sorted(update.scopes)}

    @router.get("/participant/{participant_id}")
    def get_consent(participant_id: str) -> dict:
        scopes = consent_manager.get_scopes(participant_id)
        if not scopes:
            raise HTTPException(status_code=404, detail="No consent recorded")
        return {"participant_id": participant_id, "scopes": scopes}

    return router
