"""
CR-006: Build Collective MPG by detecting cross-participant echoes of segments.

Steps:
- Load Segment nodes (expects participant_id on segments).
- Compute similarity on basic properties.
- Create ECHO_SEGMENT relationships across participants.
- Cluster echoed segments into CollectiveSegments and aggregate properties.
- Build collective edges from member segment edges.
"""

from __future__ import annotations

import os
import uuid
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Set

import networkx as nx
import numpy as np
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


class CollectiveNeo4j:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def init_schema(self) -> None:
        self.run(
            """
            CREATE CONSTRAINT group_id IF NOT EXISTS FOR (g:Group) REQUIRE g.id IS UNIQUE;
            CREATE CONSTRAINT groupsession_id IF NOT EXISTS FOR (gs:GroupSession) REQUIRE gs.id IS UNIQUE;
            CREATE CONSTRAINT grouptrial_id IF NOT EXISTS FOR (gt:GroupTrial) REQUIRE gt.id IS UNIQUE;
            CREATE CONSTRAINT collective_segment_id IF NOT EXISTS FOR (cs:CollectiveSegment) REQUIRE cs.id IS UNIQUE;
            """
        )

    def fetch_segments(self) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (s:Segment)
            RETURN s
            """
        )
        return [dict(r["s"]) for r in records]

    def fetch_segment_edges(self) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (a:Segment)-[r]->(b:Segment)
            RETURN a.id AS src, b.id AS dst, type(r) AS rel_type, r.strength AS strength, r.confidence AS confidence
            """
        )
        return [dict(r) for r in records]

    def create_echo(self, src: str, dst: str, similarity: float, basis: str = "numeric_props") -> None:
        self.run(
            """
            MATCH (a:Segment {id: $src}), (b:Segment {id: $dst})
            MERGE (a)-[r:ECHO_SEGMENT]->(b)
            SET r.similarity = $sim, r.basis = $basis, r.demo = true
            """,
            src=src,
            dst=dst,
            sim=similarity,
            basis=basis,
        )

    def create_collective_segment(self, member_ids: List[str], participant_ids: List[str], props: Dict[str, float]) -> str:
        cs_id = str(uuid.uuid4())
        self.run(
            """
            CREATE (c:CollectiveSegment {
                id: $id,
                name: $name,
                member_segment_ids: $member_ids,
                participant_ids: $participant_ids,
                valence: $valence,
                intensity: $intensity,
                confidence: $confidence,
                cohesion: $cohesion,
                potency: $potency,
                level: $level,
                rv: false,
                rv_score: 0.0,
                demo: true
            })
            """,
            id=cs_id,
            name=props.get("name", f"Collective {cs_id[:6]}"),
            member_ids=member_ids,
            participant_ids=participant_ids,
            valence=props.get("valence", 0.0),
            intensity=props.get("intensity", 0.0),
            confidence=props.get("confidence", 0.0),
            cohesion=props.get("cohesion", 0.0),
            potency=props.get("potency", 0.0),
            level=props.get("level", 2),
        )
        for mid in member_ids:
            self.run(
                """
                MATCH (c:CollectiveSegment {id: $cid}), (s:Segment {id: $sid})
                MERGE (c)-[:AGGREGATES]->(s)
                """,
                cid=cs_id,
                sid=mid,
            )
        return cs_id

    def create_collective_edge(self, src_cs: str, dst_cs: str, rel_type: str, strength: float, confidence: float) -> None:
        self.run(
            f"""
            MATCH (a:CollectiveSegment {{id: $src}}), (b:CollectiveSegment {{id: $dst}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r.strength = $strength, r.confidence = $confidence, r.demo = true
            """,
            src=src_cs,
            dst=dst_cs,
            strength=strength,
            confidence=confidence,
        )


def segment_embedding(seg: Dict[str, Any]) -> np.ndarray:
    fields = ["valence", "intensity", "recency", "stability", "importance", "confidence"]
    vec = np.array([float(seg.get(f, 0.0)) for f in fields], dtype=float)
    return vec


def cosine_sim(a: np.ndarray, b: np.ndarray, eps: float = 1e-8) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + eps
    return float(np.dot(a, b) / denom)


def build_echoes(db: CollectiveNeo4j, sim_threshold: float = 0.7) -> List[Tuple[str, str, float]]:
    segments = db.fetch_segments()
    sim_edges: List[Tuple[str, str, float]] = []
    for i, s1 in enumerate(segments):
        pid1 = s1.get("participant_id", "unknown")
        v1 = segment_embedding(s1)
        for j in range(i + 1, len(segments)):
            s2 = segments[j]
            pid2 = s2.get("participant_id", "unknown")
            if pid1 == pid2:
                continue
            v2 = segment_embedding(s2)
            sim = cosine_sim(v1, v2)
            if sim >= sim_threshold:
                sim_edges.append((s1["id"], s2["id"], sim))
                db.create_echo(s1["id"], s2["id"], sim)
    return sim_edges


def cluster_collective_segments(sim_edges: List[Tuple[str, str, float]]) -> List[Set[str]]:
    g = nx.Graph()
    for src, dst, sim in sim_edges:
        g.add_edge(src, dst, weight=sim)
    return list(nx.connected_components(g))


def aggregate_props(members: List[Dict[str, Any]], sim_edges: List[Tuple[str, str, float]], member_ids: Set[str]) -> Dict[str, float]:
    def mean(vals: List[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    valence = mean([float(m.get("valence", 0.0)) for m in members])
    intensity = mean([float(m.get("intensity", 0.0)) for m in members])
    confidence = mean([float(m.get("confidence", 0.0)) for m in members])

    # cohesion: average similarity among edges inside the cluster
    sims = [sim for a, b, sim in sim_edges if a in member_ids and b in member_ids]
    cohesion = mean(sims)

    return {
        "valence": valence,
        "intensity": intensity,
        "confidence": confidence,
        "cohesion": cohesion,
        "potency": 0.0,
        "level": 2,
    }


def build_collective_edges(db: CollectiveNeo4j, cs_members: Dict[str, Set[str]], seg_edges: List[Dict[str, Any]]) -> None:
    # index member -> collective
    member_to_cs: Dict[str, str] = {}
    for cs_id, mids in cs_members.items():
        for mid in mids:
            member_to_cs[mid] = cs_id

    # aggregate edges between collective segments
    edge_accum: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for e in seg_edges:
        src_cs = member_to_cs.get(e["src"])
        dst_cs = member_to_cs.get(e["dst"])
        if not src_cs or not dst_cs or src_cs == dst_cs:
            continue
        edge_accum[(src_cs, dst_cs)].append(e)

    for (src_cs, dst_cs), edges in edge_accum.items():
        strengths = [float(ed.get("strength", 0.0)) for ed in edges]
        confidences = [float(ed.get("confidence", 0.0)) for ed in edges]
        rel_type = edges[0].get("rel_type", "LINK")
        strength = sum(strengths) / len(strengths) if strengths else 0.0
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        db.create_collective_edge(src_cs, dst_cs, rel_type, strength, confidence)


def main() -> None:
    db = CollectiveNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        db.init_schema()
        sim_edges = build_echoes(db)
        if not sim_edges:
            print("No cross-participant echoes found (need segments with participant_id).")
            return

        clusters = cluster_collective_segments(sim_edges)
        if not clusters:
            print("No collective clusters formed.")
            return

        segments = {s["id"]: s for s in db.fetch_segments()}
        cs_members: Dict[str, Set[str]] = {}
        for cluster in clusters:
            participants = {segments[mid].get("participant_id", "unknown") for mid in cluster}
            if len(participants) < 2:
                continue
            props = aggregate_props([segments[mid] for mid in cluster], sim_edges, cluster)
            cs_id = db.create_collective_segment(
                member_ids=list(cluster),
                participant_ids=list(participants),
                props=props,
            )
            cs_members[cs_id] = set(cluster)

        if not cs_members:
            print("No CollectiveSegments created (clusters lacked participant diversity).")
            return

        seg_edges = db.fetch_segment_edges()
        build_collective_edges(db, cs_members, seg_edges)
        print(f"Created {len(cs_members)} CollectiveSegments and aggregated edges.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
