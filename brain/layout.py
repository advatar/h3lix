from __future__ import annotations

import math
from typing import Dict, Iterable, Optional

import networkx as nx
import numpy as np

from brain.models import GraphSnapshot, Position, VisualEdge, VisualNode


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _to_hex(r: float, g: float, b: float) -> str:
    r_i = int(_clamp(r) * 255)
    g_i = int(_clamp(g) * 255)
    b_i = int(_clamp(b) * 255)
    return f"#{r_i:02x}{g_i:02x}{b_i:02x}"


def _node_color(importance: float, confidence: float, valence: Optional[float]) -> str:
    cold = (0.2, 0.6, 1.0)
    warm = (1.0, 0.35, 0.2)
    mix_ratio = _clamp((valence + 1.0) / 2.0, 0.0, 1.0) if valence is not None else 0.4
    base = tuple(cold[i] + (warm[i] - cold[i]) * mix_ratio for i in range(3))
    brightness = 0.5 + 0.45 * _clamp(confidence, 0.0, 1.0)
    scaled = tuple(_clamp(b * brightness, 0.0, 1.0) for b in base)
    return _to_hex(*scaled)


def _edge_color(strength: float) -> str:
    scaled = _clamp(abs(strength), 0.0, 1.0)
    return _to_hex(0.5 * scaled, 0.7 * scaled + 0.2, 0.9 * scaled + 0.05)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _position_from_layout(node_id: str, layout: Dict[str, Iterable[float]]) -> Position:
    raw = layout.get(node_id)
    if raw is None:
        return Position(x=0.0, y=0.0, z=0.0)
    coords = list(raw)
    x = float(coords[0]) if len(coords) > 0 else 0.0
    y = float(coords[1]) if len(coords) > 1 else 0.0
    z = float(coords[2]) if len(coords) > 2 else 0.0
    return Position(x=x, y=y, z=z)


def build_graph_snapshot(
    graph: nx.DiGraph,
    level: Optional[int] = None,
    layout_seed: int = 13,
    layout_algo: str = "spring",
) -> GraphSnapshot:
    if graph.number_of_nodes() == 0:
        return GraphSnapshot(level=level, layout=layout_algo, nodes=[], edges=[])

    if layout_algo == "spring":
        layout = nx.spring_layout(graph, dim=3, seed=layout_seed)
    elif layout_algo == "spectral":
        layout_2d = nx.spectral_layout(graph, dim=2)
        layout = {k: np.array([v[0], v[1], 0.0]) for k, v in layout_2d.items()}
    else:
        layout = nx.random_layout(graph, dim=3)

    nodes: list[VisualNode] = []
    for node_id, data in graph.nodes(data=True):
        importance = _safe_float(data.get("importance"), 0.0)
        confidence = _safe_float(data.get("confidence"), 0.0)
        valence = data.get("valence")
        labels = [str(lbl) for lbl in data.get("labels", [])]
        nodes.append(
            VisualNode(
                id=str(node_id),
                name=str(data.get("name") or node_id),
                level=int(data.get("level", 0) or 0),
                importance=importance,
                confidence=confidence,
                labels=labels,
                position=_position_from_layout(node_id, layout),
                color=_node_color(importance, confidence, valence if isinstance(valence, (int, float)) else None),
                size=0.6 + 1.4 * _clamp(importance, 0.0, 1.0),
                valence=valence if isinstance(valence, (int, float)) else None,
            )
        )

    edges: list[VisualEdge] = []
    for src, dst, data in graph.edges(data=True):
        strength = _safe_float(data.get("strength"), 0.0)
        edges.append(
            VisualEdge(
                src=str(src),
                dst=str(dst),
                rel_type=str(data.get("rel_type") or data.get("type") or "RELATED"),
                strength=strength,
                confidence=_safe_float(data.get("confidence"), 0.0),
                color=_edge_color(strength),
            )
        )

    return GraphSnapshot(level=level, layout=layout_algo, nodes=nodes, edges=edges)
