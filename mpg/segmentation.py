from __future__ import annotations

import uuid
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import networkx as nx

from mpg.models import MPGEdge, MPGNode
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository


def segment_graph(graph: nx.DiGraph, strength_threshold: float = 0.6, min_size: int = 3) -> List[Set[str]]:
    strong_edges = [
        (u, v)
        for u, v, data in graph.edges(data=True)
        if data.get("strength", 0.0) >= strength_threshold
    ]
    subgraph = graph.edge_subgraph(strong_edges).copy()
    segments: List[Set[str]] = []
    for comp in nx.weakly_connected_components(subgraph):
        if len(comp) >= min_size:
            segments.append(set(comp))
    return segments


def boundary_nodes(graph: nx.DiGraph, segment_nodes: Set[str]) -> Set[str]:
    boundary: Set[str] = set()
    for node in segment_nodes:
        for neighbor in graph.successors(node):
            if neighbor not in segment_nodes:
                boundary.add(node)
        for neighbor in graph.predecessors(node):
            if neighbor not in segment_nodes:
                boundary.add(node)
    return boundary


def _mean(values: Iterable[float], default: float = 0.0) -> float:
    items = list(values)
    return sum(items) / len(items) if items else default


def aggregate_segment_node(graph: nx.DiGraph, nodes: Set[str], level: int, name: str) -> MPGNode:
    data_points = [graph.nodes[n] for n in nodes]
    return MPGNode(
        id=str(uuid.uuid4()),
        name=name,
        layers=sorted({layer for d in data_points for layer in d.get("layers", [])}),
        valence=_mean(d.get("valence", 0.0) for d in data_points),
        intensity=_mean(d.get("intensity", 0.0) for d in data_points),
        recency=_mean(d.get("recency", 0.0) for d in data_points),
        stability=_mean(d.get("stability", 0.0) for d in data_points),
        importance=_mean(d.get("importance", 0.0) for d in data_points),
        confidence=_mean(d.get("confidence", 0.0) for d in data_points),
        reasoning=f"Aggregated segment of {len(nodes)} nodes",
        level=level,
    )


def aggregate_segment_edge(graph: nx.DiGraph, src_nodes: Set[str], dst_nodes: Set[str]) -> Tuple[str, float, float]:
    strengths: List[float] = []
    confidences: List[float] = []
    rel_types: List[str] = []
    for u in src_nodes:
        for v in dst_nodes:
            if graph.has_edge(u, v):
                data = graph.get_edge_data(u, v)
                strengths.append(data.get("strength", 0.0))
                confidences.append(data.get("confidence", 0.0))
                rel_types.append(data.get("rel_type", "LINK"))
    dominant_rel = rel_types[0] if rel_types else "LINK"
    return dominant_rel, _mean(strengths, default=0.0), _mean(confidences, default=0.0)


def lift_level(
    repo: Neo4jMPGRepository | InMemoryMPGRepository,
    level: int,
    strength_threshold: float = 0.6,
    min_size: int = 3,
) -> List[MPGNode]:
    base_graph = repo.get_graph(level=level)
    segments = segment_graph(base_graph, strength_threshold=strength_threshold, min_size=min_size)
    created_segments: List[MPGNode] = []
    next_level = level + 1

    segment_nodes: List[Tuple[MPGNode, Set[str]]] = []
    for idx, nodes in enumerate(segments):
        name = f"Segment {idx + 1} (level {next_level})"
        segment_node = aggregate_segment_node(base_graph, nodes, next_level, name)
        repo.create_node(segment_node, label="Segment")
        created_segments.append(segment_node)
        segment_nodes.append((segment_node, nodes))

    for src_seg, src_nodes in segment_nodes:
        for dst_seg, dst_nodes in segment_nodes:
            if src_seg.id == dst_seg.id:
                continue
            if _has_cross_edges(base_graph, src_nodes, dst_nodes):
                rel_type, strength, confidence = aggregate_segment_edge(base_graph, src_nodes, dst_nodes)
                edge = MPGEdge(
                    src=src_seg.id,
                    dst=dst_seg.id,
                    rel_type=rel_type if rel_type else "LINK",
                    strength=strength,
                    confidence=confidence,
                    reasoning="Aggregated inter-segment relationship",
                )
                repo.create_edge(edge)

    return created_segments


def _has_cross_edges(graph: nx.DiGraph, src_nodes: Set[str], dst_nodes: Set[str]) -> bool:
    for u in src_nodes:
        for v in dst_nodes:
            if graph.has_edge(u, v):
                return True
    return False
