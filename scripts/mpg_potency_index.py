"""
CR-003: Temporal Impact Factors & Potency Index for MPG segments.

Computes Rate of Change, Breadth of Impact, Amplification, Affective Load,
Gate Leverage, Robustness, normalizes factors, and writes Potency into the
latest SegmentState and Segment.
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j-password")
HISTORY_K = 5
MAX_CYCLE_LEN = 3
EPS = 1e-8


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
        return [dict(r["s"]) for r in records]

    def get_segment_states(self, seg_id: str, k: int) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (:Segment {id: $id})-[:HAS_STATE]->(st:SegmentState)
            RETURN st
            ORDER BY st.t DESC
            LIMIT $k
            """,
            id=seg_id,
            k=k,
        )
        return [dict(r["st"]) for r in records]

    def get_latest_state(self, seg_id: str) -> Optional[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (:Segment {id: $id})-[:HAS_STATE]->(st:SegmentState)
            RETURN st
            ORDER BY st.t DESC
            LIMIT 1
            """,
            id=seg_id,
        )
        return dict(records[0]["st"]) if records else None

    def get_segment_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for seg in self.get_segments():
            graph.add_node(seg["id"], **seg)

        for rec in self.run(
            """
            MATCH (s:Segment)-[r]->(t:Segment)
            WHERE s.demo = true AND t.demo = true
            RETURN s.id AS src, t.id AS dst, type(r) AS rel_type, r.strength AS strength
            """
        ):
            graph.add_edge(
                rec["src"],
                rec["dst"],
                rel_type=rec["rel_type"],
                strength=float(rec["strength"] or 0.0),
            )
        return graph

    def get_segment_members(self, seg_id: str) -> List[Dict[str, Any]]:
        records = self.run(
            """
            MATCH (s:Segment {id: $id})
            WITH s, s.members AS member_ids
            UNWIND member_ids AS mid
            MATCH (n:MPGNode {id: mid})
            RETURN n
            """,
            id=seg_id,
        )
        return [dict(r["n"]) for r in records]

    def get_boundary_nodes(self, seg_id: str) -> List[str]:
        records = self.run(
            """
            MATCH (s:Segment {id: $id})
            WITH s, s.members AS member_ids
            UNWIND member_ids AS mid
            MATCH (n:MPGNode {id: mid})
            OPTIONAL MATCH (n)-[r]->(m:MPGNode)
            WHERE NOT m.id IN member_ids
            WITH n, collect(r) AS rs
            WHERE size(rs) > 0
            RETURN n.id AS id
            """,
            id=seg_id,
        )
        return [r["id"] for r in records]

    def update_segmentstate_potency(
        self,
        state_id: str,
        roc: float,
        boi: float,
        ampl: float,
        aff: float,
        gate: float,
        robust: float,
        potency: float,
    ) -> None:
        self.run(
            """
            MATCH (st:SegmentState {id: $id})
            SET st.roc = $roc,
                st.boi = $boi,
                st.amplification = $ampl,
                st.affective_load = $aff,
                st.gate_leverage = $gate,
                st.robustness = $robust,
                st.potency = $potency
            """,
            id=state_id,
            roc=float(roc),
            boi=float(boi),
            ampl=float(ampl),
            aff=float(aff),
            gate=float(gate),
            robust=float(robust),
            potency=float(potency),
        )

    def update_segment_latest_potency(self, seg_id: str, potency: float) -> None:
        self.run(
            """
            MATCH (s:Segment {id: $id})
            SET s.potency_latest = $p
            """,
            id=seg_id,
            p=float(potency),
        )


def rate_of_change(states: List[Dict[str, Any]]) -> float:
    if len(states) < 2:
        return 0.0
    t_vals = [float(st.get("t", 0.0)) for st in reversed(states)]
    scores = [float(st.get("rv_score", 0.0)) for st in reversed(states)]
    dt = t_vals[-1] - t_vals[0]
    if abs(dt) < EPS:
        return 0.0
    return (scores[-1] - scores[0]) / dt


def persistence(states: List[Dict[str, Any]]) -> float:
    if not states:
        return 0.0
    rv_flags = [bool(st.get("rv", False)) for st in states]
    return sum(rv_flags) / len(rv_flags)


def breadth_of_impact(graph: nx.DiGraph, seg_id: str) -> float:
    if seg_id not in graph:
        return 0.0
    deg_out = graph.out_degree(seg_id)
    w_out_sum = sum(d.get("strength", 0.0) for _, _, d in graph.out_edges(seg_id, data=True))
    levels = set()
    for node in nx.single_source_shortest_path_length(graph, seg_id, cutoff=2).keys():
        levels.add(int(graph.nodes[node].get("level", 1)))
    levels_spanned = max(levels) - min(levels) if levels else 0
    return w_out_sum * (1 + math.log1p(deg_out)) * (1 + 0.2 * levels_spanned)


def amplification(graph: nx.DiGraph, seg_id: str, max_cycle_len: int = MAX_CYCLE_LEN) -> float:
    if seg_id not in graph:
        return 0.0
    cycles = []
    for cycle in nx.simple_cycles(graph):
        if seg_id in cycle and 2 <= len(cycle) <= max_cycle_len:
            cycles.append(cycle)
    if not cycles:
        return 0.0
    strengths: List[float] = []
    for cycle in cycles:
        edges = list(zip(cycle, cycle[1:] + [cycle[0]]))
        s_sum = 0.0
        for u, v in edges:
            if graph.has_edge(u, v):
                s_sum += graph.edges[u, v].get("strength", 0.0)
        strengths.append(s_sum / len(edges) if edges else 0.0)
    return len(cycles) + 0.5 * (sum(strengths) / len(strengths))


def affective_load(member_nodes: List[Dict[str, Any]]) -> float:
    if not member_nodes:
        return 0.0
    vals = []
    for n in member_nodes:
        valence = float(n.get("valence", 0.0))
        intensity = float(n.get("intensity", 0.5))
        vals.append(abs(valence) * intensity)
    return sum(vals) / len(vals)


def gate_leverage(boundary_nodes: List[str], total_members: int) -> float:
    if total_members <= 0:
        return 0.0
    gate_ratio = len(boundary_nodes) / total_members
    return max(0.0, 1.0 - gate_ratio)


def robustness(conf_avg: float, persist: float) -> float:
    return 0.6 * conf_avg + 0.4 * persist


def normalize_factor(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    vmin = min(values.values())
    vmax = max(values.values())
    if abs(vmax - vmin) < EPS:
        return {k: 0.0 for k in values.keys()}
    return {k: (v - vmin) / (vmax - vmin) for k, v in values.items()}


def compute_potency() -> None:
    db = MPGNeo4j(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        segments = db.get_segments()
        if not segments:
            print("No segments found.")
            return

        graph = db.get_segment_graph()

        roc_raw: Dict[str, float] = {}
        boi_raw: Dict[str, float] = {}
        ampl_raw: Dict[str, float] = {}
        aff_raw: Dict[str, float] = {}
        gate_raw: Dict[str, float] = {}
        rob_raw: Dict[str, float] = {}
        latest_state_id: Dict[str, str] = {}
        latest_potency: Dict[str, float] = {}

        for seg in segments:
            seg_id = seg["id"]
            states = db.get_segment_states(seg_id, HISTORY_K)
            if not states:
                continue

            roc_val = max(0.0, rate_of_change(states))
            roc_raw[seg_id] = roc_val
            persist_val = persistence(states)

            boi_val = breadth_of_impact(graph, seg_id)
            boi_raw[seg_id] = boi_val

            ampl_val = amplification(graph, seg_id)
            ampl_raw[seg_id] = ampl_val

            members = db.get_segment_members(seg_id)
            aff_val = affective_load(members)
            aff_raw[seg_id] = aff_val

            boundary = db.get_boundary_nodes(seg_id)
            gate_val = gate_leverage(boundary, total_members=len(members))
            gate_raw[seg_id] = gate_val

            conf_avg = float(seg.get("confidence", 0.5))
            rob_val = robustness(conf_avg, persist_val)
            rob_raw[seg_id] = rob_val

            latest = db.get_latest_state(seg_id)
            if latest:
                latest_state_id[seg_id] = latest["id"]

        roc_norm = normalize_factor(roc_raw)
        boi_norm = normalize_factor(boi_raw)
        ampl_norm = normalize_factor(ampl_raw)
        aff_norm = normalize_factor(aff_raw)
        gate_norm = normalize_factor(gate_raw)
        rob_norm = normalize_factor(rob_raw)

        w_roc, w_boi, w_ampl, w_aff, w_gate, w_rob = 0.2, 0.2, 0.2, 0.15, 0.1, 0.15

        for seg_id in latest_state_id.keys():
            potency = (
                w_roc * roc_norm.get(seg_id, 0.0)
                + w_boi * boi_norm.get(seg_id, 0.0)
                + w_ampl * ampl_norm.get(seg_id, 0.0)
                + w_aff * aff_norm.get(seg_id, 0.0)
                + w_gate * gate_norm.get(seg_id, 0.0)
                + w_rob * rob_norm.get(seg_id, 0.0)
            )
            latest_potency[seg_id] = potency

        for seg_id, state_id in latest_state_id.items():
            db.update_segmentstate_potency(
                state_id,
                roc=roc_raw.get(seg_id, 0.0),
                boi=boi_raw.get(seg_id, 0.0),
                ampl=ampl_raw.get(seg_id, 0.0),
                aff=aff_raw.get(seg_id, 0.0),
                gate=gate_raw.get(seg_id, 0.0),
                robust=rob_raw.get(seg_id, 0.0),
                potency=latest_potency.get(seg_id, 0.0),
            )
            db.update_segment_latest_potency(seg_id, latest_potency.get(seg_id, 0.0))

        print(f"Potency Index updated for {len(latest_potency)} segments.")
    finally:
        db.close()


if __name__ == "__main__":
    compute_potency()
