from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from jsonschema import validate, ValidationError
from pydantic import BaseModel


class ExperimentEntry(BaseModel):
    experiment_id: str
    condition_id: str
    metrics: Dict[str, float]


class Submission(BaseModel):
    team_id: str
    architecture_name: str
    contact: str | None = None
    experiments: List[ExperimentEntry]
    notes: str | None = None


LEADERBOARD_DB = Path("results/leaderboard.db")
SCHEMA_PATH = Path("schemas/manifest.schema.json")

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


def _init_db() -> None:
    LEADERBOARD_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(LEADERBOARD_DB)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT,
                architecture_name TEXT,
                contact TEXT,
                experiments_json TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    finally:
        conn.close()


def _save_submission(submission: Dict[str, Any]) -> None:
    conn = sqlite3.connect(LEADERBOARD_DB)
    try:
        conn.execute(
            "INSERT INTO submissions (team_id, architecture_name, contact, experiments_json, notes) VALUES (?, ?, ?, ?, ?)",
            (
                submission.get("team_id"),
                submission.get("architecture_name"),
                submission.get("contact"),
                json.dumps(submission.get("experiments", [])),
                submission.get("notes"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


@router.post("/submit")
def submit(payload: Submission) -> Dict[str, Any]:
    # schema validation
    try:
        schema = json.loads(SCHEMA_PATH.read_text())
        validate(instance=payload.model_dump(), schema=schema)
    except (FileNotFoundError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid submission: {e}")
    submission = payload.model_dump()
    _save_submission(submission)
    return {"status": "accepted"}


@router.get("/leaderboard/{experiment_id}")
def leaderboard(experiment_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(LEADERBOARD_DB)
    try:
        rows = conn.execute("SELECT team_id, architecture_name, experiments_json FROM submissions ORDER BY created_at DESC").fetchall()
    finally:
        conn.close()
    filtered: List[Dict[str, Any]] = []
    for team_id, arch, exp_json in rows:
        try:
            experiments = json.loads(exp_json)
        except json.JSONDecodeError:
            experiments = []
        for exp in experiments:
            if exp.get("experiment_id") == experiment_id:
                filtered.append(
                    {
                        "team_id": team_id,
                        "architecture_name": arch,
                        "condition_id": exp.get("condition_id"),
                        "metrics": exp.get("metrics"),
                    }
                )
    if not filtered:
        raise HTTPException(status_code=404, detail="No submissions for this experiment")
    return filtered


_init_db()
