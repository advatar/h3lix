"""
Minimal H3LIX Mirrored Profile Graph prototype for CR-001:
- Creates a level-0 MPG in Neo4j
- Segments the graph in NetworkX and Lifts to level-1 segments
- Runs a simple Rogue Variable (RV) detection over segments
"""

from __future__ import annotations

import math
import os
import statistics
import uuid
from dataclasses import dataclass
from typing import Dict, List, Tuple

import networkx as nx
from neo4j import GraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")


@dataclass
class EvidenceItem:
    id: str
    description: str
    source_type: str
    pointer: str
    snippet: str
    c: float  # support
    q: float  # quality multiplier
    u: float  # diversity bonus
    t: float  # timeliness factor


def compute_confidence(evidence: List[EvidenceItem], alpha: float = 0.3) -> float:
    """Eq. (1): Conf(x) = 1 - exp(-alpha * sum(c_i * q_i * u_i * t_i))."""
    support = sum(e.c * e.q * e.u * e.t for e in evidence)
    return 1.0 - math.exp(-alpha * support)


class MPGNeo4j:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def init_schema(self) -> None:
        cypher = """
        CREATE CONSTRAINT mpgnode_id IF NOT EXISTS
        FOR (n:MPGNode) REQUIRE n.id IS UNIQUE;

        CREATE CONSTRAINT segment_id IF NOT EXISTS
        FOR (s:Segment) REQUIRE s.id IS UNIQUE;

        CREATE CONSTRAINT evidence_id IF NOT EXISTS
        FOR (e:Evidence) REQUIRE e.id IS UNIQUE;

        CREATE INDEX mpgnode_level IF NOT EXISTS
        FOR (n:MPGNode) ON (n.level);
        """
        with self.driver.session() as session:
            session.run(cypher)

    def clear_demo_data(self) -> None:
        self.run(
            """
            MATCH (n)
            WHERE n.demo = true
            DETACH DELETE n
            """
        )

    def create_node(
        self,
        name: str,
        layers: List[str],
        level: int = 0,
        valence: float = 0.0,
        intensity: float = 0.5,
        recency: float = 0.5,
        stability: float = 0.5,
        importance: float = 0.5,
        confidence: float = 0.5,
        reasoning: str | None = None,
    ) -> str:
        node_id = str(uuid.uuid4())
        res = self.run(
            """
            CREATE (n:MPGNode {
                id: $id,
                name: $name,
                layers: $layers,
                level: $level,
                valence: $valence,
                intensity: $intensity,
                recency: $recency,
                stability: $stability,
                importance: $importance,
                confidence: $confidence,
                reasoning: coalesce($reasoning, ""),
                demo: true,
                rv: false
            })
            RETURN n.id AS id
            """,
            id=node_id,
            name=name,
            layers=layers,
            level=level,
            valence=valence,
            intensity=intensity,
            recency=recency,
            stability=stability,
            importance=importance,
            confidence=confidence,
            reasoning=reasoning,
        )
        return res[0]["id"]

    def create_edge(
        self,
        src_id: str,
        dst_id: str,
        rel_type: str,
        strength: float = 0.5,
        confidence: float = 0.5,
        description: str | None = None,
    ) -> None:
        self.run(
            f"""
            MATCH (a:MPGNode {{id: $src_id}}),
                  (b:MPGNode {{id: $dst_id}})
            CREATE (a)-[r:{rel_type} {{
                strength: $strength,
                confidence: $confidence,
                description: coalesce($description, ""),
                demo: true
            }}]->(b)
            """,
            src_id=src_id,
            dst_id=dst_id,
            strength=strength,
            confidence=confidence,
            description=description,
        )

    def load_level0_as_networkx(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        nodes = self.run(
            """
            MATCH (n:MPGNode)
            WHERE n.demo = true AND n.level = 0
            RETURN n
            """
        )
        for record in nodes:
            node = record["n"]
            graph.add_node(node["id"], **dict(node))

        edges = self.run(
            """
            MATCH (a:MPGNode)-[r]->(b:MPGNode)
            WHERE a.demo = true AND b.demo = true AND a.level = 0 AND b.level = 0
            RETURN a.id AS src, b.id AS dst, type(r) AS rel_type, r
            """
        )
        for record in edges:
            props = dict(record["r"])
            props["rel_type"] = record["rel_type"]
            graph.add_edge(record["src"], record["dst"], **props)
        return graph

    def create_segment_node(
        self,
        member_node_ids: List[str],
        level: int,
        agg_props: Dict[str, float | str | List[str]],
        name: str,
    ) -> str:
        seg_id = str(uuid.uuid4())
        res = self.run(
            """
            CREATE (s:Segment {
                id: $id,
                name: $name,
                level: $level,
                members: $members,
                layers: $layers,
                valence: $valence,
                intensity: $intensity,
                recency: $recency,
                stability: $stability,
                importance: $importance,
                confidence: $confidence,
                reasoning: $reasoning,
                demo: true,
                rv: false
            })
            RETURN s.id AS id
            """,
            id=seg_id,
            name=name,
            level=level,
            members=member_node_ids,
            layers=agg_props.get("layers", []),
            valence=agg_props["valence"],
            intensity=agg_props["intensity"],
            recency=agg_props["recency"],
            stability=agg_props["stability"],
            importance=agg_props["importance"],
            confidence=agg_props["confidence"],
            reasoning=agg_props["reasoning"],
        )
        return res[0]["id"]

    def create_segment_edge(
        self,
        src_seg_id: str,
        dst_seg_id: str,
        rel_type: str,
        strength: float,
        confidence: float,
        description: str,
    ) -> None:
        self.run(
            f"""
            MATCH (s:Segment {{id: $src_id}}),
                  (t:Segment {{id: $dst_id}})
            CREATE (s)-[r:{rel_type} {{
                strength: $strength,
                confidence: $confidence,
                description: $description,
                demo: true
            }}]->(t)
            """,
            src_id=src_seg_id,
            dst_id=dst_seg_id,
            strength=strength,
            confidence=confidence,
            description=description,
        )

    def mark_segment_as_rv(self, seg_id: str, rv_score: float, potency: float) -> None:
        self.run(
            """
            MATCH (s:Segment {id: $id})
            SET s.rv = true,
                s.rv_score = $rv_score,
                s.potency = $potency
            """,
            id=seg_id,
            rv_score=rv_score,
            potency=potency,
        )


def seed_example_graph(db: MPGNeo4j) -> None:
    """Create a small graph inspired by Figures 1–3 with contradictions and strong ties."""
    db.clear_demo_data()
    n_values = db.create_node(
        "Core values: autonomy",
        ["Psychological"],
        valence=0.8,
        intensity=0.7,
        reasoning="From interview: autonomy highly valued",
    )
    n_job = db.create_node(
        "Current job demands obedience",
        ["Professional"],
        valence=-0.3,
        intensity=0.6,
        reasoning="Job description & self-report",
    )
    n_coping = db.create_node(
        "Coping: suppress opinion at work",
        ["CopingRoutine"],
        valence=-0.6,
        intensity=0.8,
        reasoning="Self-report: often stays silent in meetings",
    )
    n_goal = db.create_node(
        "Goal: be seen as collaborative",
        ["Psychological"],
        valence=0.5,
        intensity=0.5,
    )
    n_stress = db.create_node(
        "Somatic: chronic tension",
        ["Somatic"],
        valence=-0.7,
        intensity=0.9,
    )

    db.create_edge(n_values, n_coping, "CONTRADICTS", strength=0.9, description="Autonomy vs suppression at work")
    db.create_edge(n_job, n_coping, "CAUSES", strength=0.8)
    db.create_edge(n_coping, n_stress, "TRIGGERS", strength=0.7)
    db.create_edge(n_goal, n_coping, "MODERATES", strength=0.4)
    db.create_edge(n_values, n_goal, "ALIGNS", strength=0.6)


def segment_graph(graph: nx.DiGraph, min_size: int = 2, strength_threshold: float = 0.6) -> List[List[str]]:
    """Filter strong edges then take weakly connected components."""
    strong_subgraph = graph.edge_subgraph(
        [(u, v) for u, v, d in graph.edges(data=True) if d.get("strength", 0.0) > strength_threshold]
    ).copy()
    segments: List[List[str]] = []
    for comp in nx.weakly_connected_components(strong_subgraph):
        if len(comp) >= min_size:
            segments.append(list(comp))
    return segments


def aggregate_segment_props(graph: nx.DiGraph, node_ids: List[str]) -> Dict[str, float | str | List[str]]:
    """Aggregate node properties into segment-level metrics (mean)."""
    if not node_ids:
        return {}
    numeric_keys = ["valence", "intensity", "recency", "stability", "importance", "confidence"]
    agg: Dict[str, float | str | List[str]] = {}
    layers: List[str] = []
    for key in numeric_keys:
        values = [float(graph.nodes[n].get(key, 0.5)) for n in node_ids]
        agg[key] = sum(values) / len(values) if values else 0.5
    for nid in node_ids:
        layers.extend(graph.nodes[nid].get("layers", []))
    agg["layers"] = sorted(set(layers))
    agg["reasoning"] = f"Lifted segment of {len(node_ids)} nodes"
    return agg


def build_segment_edges(graph: nx.DiGraph, segments: List[List[str]]) -> List[Tuple[int, int, Dict[str, float | str]]]:
    """Create edges between segments if base graph has crossing edges."""
    seg_edges: List[Tuple[int, int, Dict[str, float | str]]] = []
    seg_index = {i: set(seg) for i, seg in enumerate(segments)}
    for i, source_nodes in seg_index.items():
        for j, target_nodes in seg_index.items():
            if i == j:
                continue
            strengths: List[float] = []
            confidences: List[float] = []
            rel_types: List[str] = []
            for u in source_nodes:
                for v in target_nodes:
                    if graph.has_edge(u, v):
                        data = graph.get_edge_data(u, v)
                        strengths.append(float(data.get("strength", 0.5)))
                        confidences.append(float(data.get("confidence", 0.5)))
                        rel_types.append(data.get("rel_type", "LINK"))
            if strengths:
                seg_edges.append(
                    (
                        i,
                        j,
                        {
                            "strength": sum(strengths) / len(strengths),
                            "confidence": sum(confidences) / len(confidences),
                            "rel_type": rel_types[0] if rel_types else "LINK",
                        },
                    )
                )
    return seg_edges


def lift_level0_to_level1(db: MPGNeo4j) -> List[str]:
    """Definition 4 Lift(G^(0)) -> G^(1) for the demo graph."""
    graph = db.load_level0_as_networkx()
    segments = segment_graph(graph)
    if not segments:
        print("No segments found; nothing to lift.")
        return []

    segment_ids: Dict[int, str] = {}
    for idx, nodes in enumerate(segments):
        agg = aggregate_segment_props(graph, nodes)
        seg_id = db.create_segment_node(nodes, level=1, agg_props=agg, name=f"Segment {idx + 1}")
        segment_ids[idx] = seg_id

    seg_edges = build_segment_edges(graph, segments)
    for i, j, data in seg_edges:
        db.create_segment_edge(
            segment_ids[i],
            segment_ids[j],
            data["rel_type"],
            strength=float(data["strength"]),
            confidence=float(data["confidence"]),
            description="Aggregated inter-segment relationship",
        )
    return list(segment_ids.values())


def detect_rogue_segments(db: MPGNeo4j) -> None:
    """Three-sigma RV detection over segments using contribution = importance * confidence."""
    records = db.run(
        """
        MATCH (s:Segment)
        WHERE s.demo = true
        RETURN s.id AS id, s.importance AS importance, s.confidence AS confidence
        """
    )
    if not records:
        print("No segments to analyze.")
        return

    scores: List[Tuple[str, float]] = []
    for record in records:
        contribution = abs(float(record["importance"]) * float(record["confidence"]))
        scores.append((record["id"], contribution))

    values = [score for _, score in scores]
    mean = statistics.fmean(values)
    std = statistics.pstdev(values)
    threshold = mean + 3 * std
    print(f"RV threshold = {threshold:.4f} (mean={mean:.4f}, std={std:.4f})")

    for seg_id, score in scores:
        if score >= threshold:
            db.mark_segment_as_rv(seg_id, rv_score=score, potency=score)
            print(f"Segment {seg_id} marked as RV (score={score:.4f})")


def main() -> None:
    db = MPGNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        db.init_schema()
        seed_example_graph(db)
        segment_ids = lift_level0_to_level1(db)
        print(f"Created {len(segment_ids)} level-1 segments.")
        detect_rogue_segments(db)
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
