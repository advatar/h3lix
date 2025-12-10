from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict

from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository


@dataclass
class ClinicalSession:
    id: str
    participant_id: str
    clinician_id: str
    start_time: float
    end_time: Optional[float]
    mode: str
    session_number: int
    goals: List[str]
    status: str


@dataclass
class InterventionPlan:
    id: str
    name: str
    type: str
    targets: List[str]
    homework_tasks: List[str]
    intended_duration: Optional[str] = None
    success_criteria: Optional[str] = None
    risk_level: Optional[str] = None


@dataclass
class ClinicalEpisode:
    id: str
    session_id: str
    focus_segment: Optional[str]
    trial_id: Optional[str]
    title: Optional[str] = None


@dataclass
class ClinicalNote:
    id: str
    session_id: str
    author: str
    text: str


def create_clinical_session(repo: Neo4jMPGRepository | InMemoryMPGRepository, session: ClinicalSession) -> None:
    if isinstance(repo, Neo4jMPGRepository):
        repo.driver.session(database=repo.database).run(
            """
            MATCH (p:Participant {id: $pid})
            MERGE (c:Clinician {id: $cid})
            MERGE (s:ClinicalSession {id: $sid})
            SET s.participant_id = $pid,
                s.clinician_id = $cid,
                s.start_time = datetime({epochSeconds: $start}),
                s.end_time = (case when $end is null then null else datetime({epochSeconds: $end}) end),
                s.mode = $mode,
                s.session_number = $num,
                s.goals = $goals,
                s.status = $status
            MERGE (p)-[:HAS_CLINICAL_SESSION]->(s)
            MERGE (c)-[:CONDUCTS_SESSION]->(s)
            """,
            pid=session.participant_id,
            cid=session.clinician_id,
            sid=session.id,
            start=session.start_time,
            end=session.end_time,
            mode=session.mode,
            num=session.session_number,
            goals=session.goals,
            status=session.status,
        )
    else:
        repo.nodes[session.id] = session  # type: ignore[index]


def create_intervention_plan(repo: Neo4jMPGRepository | InMemoryMPGRepository, plan: InterventionPlan, participant_id: str) -> None:
    if isinstance(repo, Neo4jMPGRepository):
        repo.driver.session(database=repo.database).run(
            """
            MATCH (p:Participant {id: $pid})
            MERGE (ip:InterventionPlan {id: $id})
            SET ip.name = $name,
                ip.type = $type,
                ip.targets = $targets,
                ip.homework_tasks = $tasks,
                ip.intended_duration = $duration,
                ip.success_criteria = $success,
                ip.risk_level = $risk
            MERGE (p)-[:HAS_PLAN]->(ip)
            WITH ip, $targets AS tids
            UNWIND tids AS sid
            MATCH (s:Segment {id: sid})
            MERGE (ip)-[:TARGETS_SEGMENT]->(s)
            """,
            pid=participant_id,
            id=plan.id,
            name=plan.name,
            type=plan.type,
            targets=plan.targets,
            tasks=plan.homework_tasks,
            duration=plan.intended_duration,
            success=plan.success_criteria,
            risk=plan.risk_level,
        )
    else:
        repo.nodes[plan.id] = plan  # type: ignore[index]


def create_episode(repo: Neo4jMPGRepository | InMemoryMPGRepository, episode: ClinicalEpisode) -> None:
    if isinstance(repo, Neo4jMPGRepository):
        repo.driver.session(database=repo.database).run(
            """
            MATCH (s:ClinicalSession {id: $sid})
            MERGE (e:ClinicalEpisode {id: $eid})
            SET e.title = $title
            MERGE (s)-[:HAS_EPISODE]->(e)
            WITH e
            CALL {
              WITH e
              MATCH (t:Trial {id: $tid})
              MERGE (e)-[:LINKS_TRIAL]->(t)
            } IN TRANSACTIONS OF 1 ROW
            CALL {
              WITH e
              MATCH (seg:Segment {id: $segid})
              MERGE (e)-[:FOCUSES_SEGMENT]->(seg)
            } IN TRANSACTIONS OF 1 ROW
            """,
            sid=episode.session_id,
            eid=episode.id,
            title=episode.title,
            tid=episode.trial_id,
            segid=episode.focus_segment,
        )
    else:
        repo.nodes[episode.id] = episode  # type: ignore[index]


def create_note(repo: Neo4jMPGRepository | InMemoryMPGRepository, note: ClinicalNote) -> None:
    if isinstance(repo, Neo4jMPGRepository):
        repo.driver.session(database=repo.database).run(
            """
            MATCH (s:ClinicalSession {id: $sid})
            MERGE (n:ClinicalNote {id: $nid})
            SET n.text = $text, n.author = $author, n.created_at = datetime()
            MERGE (s)-[:HAS_NOTE]->(n)
            """,
            sid=note.session_id,
            nid=note.id,
            text=note.text,
            author=note.author,
        )
    else:
        repo.nodes[note.id] = note  # type: ignore[index]


def fetch_plans(repo: Neo4jMPGRepository | InMemoryMPGRepository, participant_id: str) -> List[Dict]:
    if isinstance(repo, Neo4jMPGRepository):
        result = repo.driver.session(database=repo.database).run(
            """
            MATCH (:Participant {id: $pid})-[:HAS_PLAN]->(ip:InterventionPlan)
            OPTIONAL MATCH (ip)-[:TARGETS_SEGMENT]->(s:Segment)
            RETURN ip, collect(s.id) AS targets
            """,
            pid=participant_id,
        )
        plans: List[Dict] = []
        for row in result:
            plan = dict(row["ip"])
            plan["targets"] = row.get("targets", [])
            plans.append(plan)
        return plans
    # In-memory fallback
    plans = []
    for node in repo.nodes.values():  # type: ignore[union-attr]
        if isinstance(node, InterventionPlan):
            plans.append(
                {
                    "id": node.id,
                    "name": node.name,
                    "type": node.type,
                    "targets": node.targets,
                    "homework_tasks": node.homework_tasks,
                    "intended_duration": node.intended_duration,
                    "success_criteria": node.success_criteria,
                    "risk_level": node.risk_level,
                }
            )
    return plans


def fetch_notes(repo: Neo4jMPGRepository | InMemoryMPGRepository, session_id: str) -> List[Dict]:
    if isinstance(repo, Neo4jMPGRepository):
        result = repo.driver.session(database=repo.database).run(
            """
            MATCH (:ClinicalSession {id: $sid})-[:HAS_NOTE]->(n:ClinicalNote)
            RETURN n
            ORDER BY n.created_at DESC
            """,
            sid=session_id,
        )
        return [dict(r["n"]) for r in result]
    notes: List[Dict] = []
    for node in repo.nodes.values():  # type: ignore[union-attr]
        if isinstance(node, ClinicalNote) and node.session_id == session_id:
            notes.append({"id": node.id, "text": node.text, "author": node.author})
    return notes


def fetch_episodes(repo: Neo4jMPGRepository | InMemoryMPGRepository, session_id: str) -> List[Dict]:
    if isinstance(repo, Neo4jMPGRepository):
        result = repo.driver.session(database=repo.database).run(
            """
            MATCH (:ClinicalSession {id: $sid})-[:HAS_EPISODE]->(e:ClinicalEpisode)
            OPTIONAL MATCH (e)-[:FOCUSES_SEGMENT]->(s:Segment)
            OPTIONAL MATCH (e)-[:LINKS_TRIAL]->(t:Trial)
            RETURN e, s.id AS segment_id, t.id AS trial_id
            """,
            sid=session_id,
        )
        episodes: List[Dict] = []
        for row in result:
            ep = dict(row["e"])
            ep["focus_segment"] = row.get("segment_id")
            ep["trial_id"] = row.get("trial_id")
            episodes.append(ep)
        return episodes
    episodes: List[Dict] = []
    for node in repo.nodes.values():  # type: ignore[union-attr]
        if isinstance(node, ClinicalEpisode) and node.session_id == session_id:
            episodes.append(
                {
                    "id": node.id,
                    "session_id": node.session_id,
                    "focus_segment": node.focus_segment,
                    "trial_id": node.trial_id,
                    "title": node.title,
                }
            )
    return episodes
