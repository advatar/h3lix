"""
CR-002/CR-004: FastAPI service exposing MPG segments, Rogue Variables, segment states, and MUFS/intuition metadata.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


class MPGNeo4j:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def get_segments(self) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (s:Segment)
            WHERE s.demo = true
            RETURN s
            """
        )
        return [dict(record["s"]) for record in records]

    def get_rv_segments(self) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (s:Segment)
            WHERE s.demo = true AND coalesce(s.rv, false) = true
            RETURN s
            """
        )
        return [dict(record["s"]) for record in records]

    def get_segment_edges(self) -> List[Dict[str, Any]]:
        return [
            dict(record)
            for record in self.run(
                """
                MATCH (s:Segment)-[r]->(t:Segment)
                WHERE s.demo = true AND t.demo = true
                RETURN s.id AS src, t.id AS dst, type(r) AS type, r.strength AS strength
                """
            )
        ]

    def get_segment_states(self, seg_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (:Segment {id: $id})-[:HAS_STATE]->(st:SegmentState)
            RETURN st
            ORDER BY st.t DESC
            LIMIT $limit
            """,
            id=seg_id,
            limit=limit,
        )
        return [dict(r["st"]) for r in records]

    def get_high_potency_low_coherence(self, potency_threshold: float, coherence_threshold: float, limit: int = 10) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (s:Segment)-[:HAS_STATE]->(st:SegmentState)
            WHERE s.demo = true
              AND coalesce(st.potency, 0.0) >= $p_thresh
              AND (st.coherence IS NULL OR st.coherence <= $c_thresh)
            RETURN s.id AS segment_id, s.name AS name, st.potency AS potency, st.coherence AS coherence, st.t AS t
            ORDER BY st.potency DESC
            LIMIT $limit
            """,
            p_thresh=potency_threshold,
            c_thresh=coherence_threshold,
            limit=limit,
        )
        return [dict(r) for r in records]

    def get_trials_intuition(self) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (t:Trial)
            RETURN t.id AS id, t.awareness_condition AS awareness, t.mpg_intuitive AS mpg_intuitive,
                   t.has_mufs AS has_mufs, t.mufs_size AS mufs_size, t.mufs_type AS mufs_type
            """
        )
        return [dict(r) for r in records]

    def get_mufs(self) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (t:Trial)-[:HAS_MUFS]->(m:MUFS)
            RETURN t.id AS trial_id, t.awareness_condition AS awareness, m.id AS mufs_id,
                   m.size AS size, m.input_keys AS input_keys
            """
        )
        return [dict(r) for r in records]


db = MPGNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

app = FastAPI(title="H3LIX MPG API (CR-002/CR-003)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
def shutdown_event() -> None:
    db.close()


@app.get("/segments")
def list_segments() -> List[Dict[str, Any]]:
    """All level-1 segments (demo)."""
    return db.get_segments()


@app.get("/segments/rv")
def list_rv_segments() -> List[Dict[str, Any]]:
    """Segments marked as Rogue Variables."""
    return db.get_rv_segments()


@app.get("/segments/edges")
def list_segment_edges() -> List[Dict[str, Any]]:
    """Directed edges between segments."""
    return db.get_segment_edges()


@app.get("/segment_states/{segment_id}")
def list_segment_states(segment_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Recent SegmentState snapshots for a segment."""
    return db.get_segment_states(segment_id, limit=limit)


@app.get("/segment_states/high_potency")
def list_high_potency_low_coherence(
    potency_threshold: float = 0.5,
    coherence_threshold: float = 0.3,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """High-potency segments under low/no coherence (Noetic hook)."""
    return db.get_high_potency_low_coherence(potency_threshold, coherence_threshold, limit=limit)


@app.get("/trials/intuition")
def list_trials_intuition() -> List[Dict[str, Any]]:
    """Trials with MUFS/intuition metadata."""
    return db.get_trials_intuition()


@app.get("/mufs")
def list_mufs() -> List[Dict[str, Any]]:
    """MUFS records and linked trial info."""
    return db.get_mufs()
