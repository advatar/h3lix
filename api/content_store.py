from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PATH = Path("results/content_store.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CohortRecord:
    cohort_id: str
    name: str
    description: Optional[str]
    member_sessions: List[str]
    created_utc: str

    @classmethod
    def new(cls, name: str, description: Optional[str], member_sessions: List[str]) -> "CohortRecord":
        return cls(
            cohort_id=str(uuid.uuid4()),
            name=name,
            description=description,
            member_sessions=member_sessions,
            created_utc=_now(),
        )


@dataclass
class LessonRecord:
    lesson_id: str
    title: str
    description_md: str
    difficulty: str
    target_audience: str
    backing_data: Dict[str, Any]
    modules: List[Dict[str, Any]]

    @classmethod
    def new(cls, payload: Dict[str, Any]) -> "LessonRecord":
        return cls(
            lesson_id=payload.get("lesson_id") or str(uuid.uuid4()),
            title=payload["title"],
            description_md=payload.get("description_md", ""),
            difficulty=payload.get("difficulty", "intro"),
            target_audience=payload.get("target_audience", "demo"),
            backing_data=payload.get("backing_data", {"kind": "synthetic", "scenario_id": "demo"}),
            modules=payload.get("modules", []),
        )


class ContentStore:
    """Lightweight JSON-backed store for cohorts, lessons, and lesson progress."""

    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            seed = {
                "cohorts": [],
                "lessons": [
                    asdict(
                        LessonRecord.new(
                            {
                                "lesson_id": "lesson-demo",
                                "title": "Immersive Walkthrough",
                                "description_md": "Demo lesson for H3LIX Vision.",
                                "difficulty": "intro",
                                "target_audience": "demo",
                                "backing_data": {"kind": "synthetic", "scenario_id": "demo"},
                                "modules": [
                                    {
                                        "module_id": "module-1",
                                        "title": "Orientation",
                                        "description_md": "Get familiar with the space.",
                                        "order": 0,
                                        "steps": [
                                            {
                                                "step_id": "step-1",
                                                "title": "Look around",
                                                "description_md": "Explore the scene.",
                                                "scene_control_delta": {"focus_node_id": None, "t_rel_ms": 0, "mode": "live"},
                                                "camera_hint": {"position": None, "look_at": None},
                                                "interaction_task": None,
                                                "quiz": None,
                                                "estimated_seconds": 15,
                                            }
                                        ],
                                    }
                                ],
                            }
                        )
                    )
                ],
                "progress": {},
            }
            self.path.write_text(json.dumps(seed, indent=2))

    def _load(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text())

    def _save(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    # Cohorts
    def list_cohorts(self) -> List[CohortRecord]:
        data = self._load()
        return [CohortRecord(**c) for c in data.get("cohorts", [])]

    def add_cohort(self, name: str, description: Optional[str], member_sessions: List[str]) -> CohortRecord:
        data = self._load()
        cohort = CohortRecord.new(name, description, member_sessions)
        data.setdefault("cohorts", []).append(asdict(cohort))
        self._save(data)
        return cohort

    def get_cohort(self, cohort_id: str) -> Optional[CohortRecord]:
        for c in self.list_cohorts():
            if c.cohort_id == cohort_id:
                return c
        return None

    # Lessons
    def list_lessons(self) -> List[LessonRecord]:
        data = self._load()
        return [LessonRecord(**l) for l in data.get("lessons", [])]

    def get_lesson(self, lesson_id: str) -> Optional[LessonRecord]:
        for l in self.list_lessons():
            if l.lesson_id == lesson_id:
                return l
        return None

    def upsert_lesson(self, payload: Dict[str, Any]) -> LessonRecord:
        data = self._load()
        lesson = LessonRecord.new(payload)
        lessons = data.setdefault("lessons", [])
        lessons = [l for l in lessons if l.get("lesson_id") != lesson.lesson_id]
        lessons.append(asdict(lesson))
        data["lessons"] = lessons
        self._save(data)
        return lesson

    # Progress
    def get_progress(self, lesson_id: str, user_id: str) -> Dict[str, Any]:
        data = self._load()
        progress = data.get("progress", {})
        key = f"{lesson_id}:{user_id}"
        return progress.get(
            key,
            {
                "user_id": user_id,
                "lesson_id": lesson_id,
                "current_module_idx": 0,
                "current_step_idx": 0,
                "completed": False,
            },
        )

    def set_progress(self, lesson_id: str, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        progress = data.setdefault("progress", {})
        key = f"{lesson_id}:{user_id}"
        progress[key] = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "current_module_idx": int(payload.get("current_module_idx", 0)),
            "current_step_idx": int(payload.get("current_step_idx", 0)),
            "completed": bool(payload.get("completed", False)),
        }
        self._save(data)
        return progress[key]
