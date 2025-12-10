from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from api.content_store import ContentStore
from schemas.api import Cohort, CohortMpgEchoResponse, CohortNoeticSummary, GroupNoeticSample, SubjectNoeticSeries, NoeticSample
from streams.models import EventRecord
from streams.store import InMemoryEventStore, PostgresEventStore


def _collect_noetic(records: List[EventRecord]) -> Dict[str, List[NoeticSample]]:
    """Extract noetic-like samples from event payloads keyed by session_id."""
    samples: Dict[str, List[NoeticSample]] = {}
    for rec in records:
        session_id = rec.event.session_id or rec.event.payload.get("session_id")
        if not session_id:
            continue
        payload = rec.event.payload or {}
        # Expect keys similar to the NoeticStatePayload schema
        if "global_coherence_score" in payload:
            try:
                sample = NoeticSample(
                    t_rel_ms=int(payload.get("t_rel_ms", 0) or 0),
                    global_coherence_score=float(payload.get("global_coherence_score", 0.0) or 0.0),
                    entropy_change=float(payload.get("entropy_change", 0.0) or 0.0),
                    band_strengths=[float(x) for x in payload.get("band_strengths", [])],
                )
            except Exception:
                continue
            samples.setdefault(session_id, []).append(sample)
    for sid in samples:
        samples[sid].sort(key=lambda s: s.t_rel_ms)
    return samples


def _group_summary(member_samples: Dict[str, List[NoeticSample]]) -> List[GroupNoeticSample]:
    # Bin by t_rel_ms if present; otherwise return empty.
    if not member_samples:
        return []
    # Build simple time-indexed list assuming equal-length arrays is not safe; flatten by t_rel_ms.
    flat: Dict[int, List[NoeticSample]] = {}
    for series in member_samples.values():
        for sample in series:
            flat.setdefault(sample.t_rel_ms, []).append(sample)
    summary: List[GroupNoeticSample] = []
    for t_rel_ms, samples in sorted(flat.items(), key=lambda kv: kv[0]):
        gcs_values = [s.global_coherence_score for s in samples]
        band_sync = []
        # Simple per-band mean for now; if bands differ lengths, skip sync.
        if samples and all(s.band_strengths for s in samples):
            max_len = min(len(s.band_strengths) for s in samples)
            if max_len > 0:
                for i in range(max_len):
                    vals = [s.band_strengths[i] for s in samples if len(s.band_strengths) > i]
                    band_sync.append(sum(vals) / len(vals) if vals else 0.0)
        summary.append(
            GroupNoeticSample(
                t_rel_ms=t_rel_ms,
                mean_global_coherence=float(statistics.fmean(gcs_values)) if gcs_values else 0.0,
                dispersion_global_coherence=float(statistics.pstdev(gcs_values)) if len(gcs_values) > 1 else 0.0,
                band_sync_index=band_sync,
            )
        )
    return summary


def build_cohorts_lessons_router(content: ContentStore, event_store: InMemoryEventStore | PostgresEventStore) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["cohorts", "lessons"])

    # Cohorts
    @router.get("/cohorts", response_model=List[Cohort])
    def list_cohorts() -> List[Dict[str, Any]]:
        return [c.__dict__ for c in content.list_cohorts()]

    @router.post("/cohorts", response_model=Cohort)
    def create_cohort(payload: Dict[str, Any]) -> Dict[str, Any]:
        name = payload.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        description = payload.get("description")
        member_sessions = payload.get("member_sessions") or []
        if not isinstance(member_sessions, list):
            raise HTTPException(status_code=400, detail="member_sessions must be a list")
        cohort = content.add_cohort(name=name, description=description, member_sessions=member_sessions)
        return cohort.__dict__

    @router.get("/cohorts/{cohort_id}", response_model=Cohort)
    def get_cohort(cohort_id: str) -> Dict[str, Any]:
        cohort = content.get_cohort(cohort_id)
        if not cohort:
            raise HTTPException(status_code=404, detail="Cohort not found")
        return cohort.__dict__

    @router.get("/cohorts/{cohort_id}/noetic-summary", response_model=CohortNoeticSummary)
    def cohort_noetic_summary(cohort_id: str, from_ms: int = 0, to_ms: int = 60_000, bin_ms: int = 1_000) -> Dict[str, Any]:
        cohort = content.get_cohort(cohort_id)
        if not cohort:
            raise HTTPException(status_code=404, detail="Cohort not found")
        members = _collect_noetic([r for r in event_store.all_records() if (r.event.session_id or r.event.payload.get("session_id")) in cohort.member_sessions])
        member_series: List[SubjectNoeticSeries] = []
        for sid, series in members.items():
            filtered = [s for s in series if from_ms <= s.t_rel_ms <= to_ms]
            member_series.append(
                SubjectNoeticSeries(
                    id=sid,
                    subject_label=sid,
                    samples=filtered,
                )
            )
        group = _group_summary({m.id: m.samples for m in member_series})
        return CohortNoeticSummary(cohort_id=cohort_id, members=member_series, group=group)

    @router.get("/cohorts/{cohort_id}/mpg-echoes", response_model=CohortMpgEchoResponse)
    def cohort_mpg_echoes(cohort_id: str, from_ms: int = 0, to_ms: int = 60_000, min_consistency: float = 0.7) -> Dict[str, Any]:
        cohort = content.get_cohort(cohort_id)
        if not cohort:
            raise HTTPException(status_code=404, detail="Cohort not found")
        # Placeholder; echo detection not yet implemented.
        return CohortMpgEchoResponse(cohort_id=cohort_id, echoes=[])

    # Lessons
    @router.get("/lessons")
    def list_lessons() -> List[Dict[str, Any]]:
        return [l.__dict__ for l in content.list_lessons()]

    @router.post("/lessons")
    def create_lesson(payload: Dict[str, Any]) -> Dict[str, Any]:
        required = ["title"]
        for key in required:
            if key not in payload:
                raise HTTPException(status_code=400, detail=f"{key} is required")
        lesson = content.upsert_lesson(payload)
        return lesson.__dict__

    @router.get("/lessons/{lesson_id}")
    def fetch_lesson(lesson_id: str) -> Dict[str, Any]:
        lesson = content.get_lesson(lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        return lesson.__dict__

    @router.get("/lessons/{lesson_id}/progress/{user_id}")
    def fetch_progress(lesson_id: str, user_id: str) -> Dict[str, Any]:
        if not content.get_lesson(lesson_id):
            raise HTTPException(status_code=404, detail="Lesson not found")
        return content.get_progress(lesson_id, user_id)

    @router.post("/lessons/{lesson_id}/progress/{user_id}")
    def update_progress(lesson_id: str, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not content.get_lesson(lesson_id):
            raise HTTPException(status_code=404, detail="Lesson not found")
        return content.set_progress(lesson_id, user_id, payload)

    return router
