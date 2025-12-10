from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Optional

import networkx as nx
try:
    from neo4j import Driver, GraphDatabase
    _neo4j_import_error = None
except Exception as exc:  # pragma: no cover - optional dependency guard
    Driver = None  # type: ignore
    GraphDatabase = None  # type: ignore
    _neo4j_import_error = exc

from mpg.models import EvidenceItem, MPGEdge, MPGNode, SegmentState


def _model_dump(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


class Neo4jMPGRepository:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j", driver: Driver | None = None):
        if GraphDatabase is None or _neo4j_import_error:
            raise RuntimeError(f"neo4j driver is unavailable: {_neo4j_import_error}")
        self.driver: Driver = driver or GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self) -> None:
        if self.driver:
            self.driver.close()

    def node_exists(self, node_id: str) -> bool:
        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (n {id: $id})
                RETURN count(n) AS cnt
                """,
                id=node_id,
            )
            rec = result.single()
            return bool(rec and rec["cnt"] > 0)

    def top_segments(self, limit: int = 5) -> List[Dict]:
        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (s:Segment)
                RETURN s
                ORDER BY coalesce(s.importance, 0) DESC, coalesce(s.confidence, 0) DESC
                LIMIT $limit
                """,
                limit=limit,
            )
            return [dict(rec["s"]) for rec in records]

    def get_segment_states(self, segment_id: str, limit: int = 5) -> List[Dict]:
        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (:Segment {id: $sid})-[:HAS_STATE]->(st:SegmentState)
                RETURN st
                ORDER BY st.t DESC
                LIMIT $limit
                """,
                sid=segment_id,
                limit=limit,
            )
            return [dict(rec["st"]) for rec in records]

    def update_segment_metadata(
        self,
        segment_id: str,
        name: Optional[str] = None,
        importance: Optional[float] = None,
        visible: Optional[bool] = None,
    ) -> None:
        updates = []
        params: Dict[str, object] = {"id": segment_id}
        if name is not None:
            updates.append("s.name = $name")
            params["name"] = name
        if importance is not None:
            updates.append("s.importance = $importance")
            params["importance"] = importance
        if visible is not None:
            updates.append("s.visible = $visible")
            params["visible"] = visible
        if not updates:
            return
        set_clause = ", ".join(updates)
        with self.driver.session(database=self.database) as session:
            session.run(
                f"""
                MATCH (s:Segment {{id: $id}})
                SET {set_clause}, s.updated_at = datetime()
                """,
                **params,
            )

    @staticmethod
    def compute_confidence(evidence_items: Iterable[EvidenceItem], alpha: float = 0.3) -> float:
        support = sum(e.c * e.q * e.u * e.t for e in evidence_items)
        return float(1 - math.exp(-alpha * support))

    def create_node(self, node: MPGNode, evidences: Optional[List[EvidenceItem]] = None, label: str = "MPGNode") -> None:
        evidences = evidences or []
        payload = _model_dump(node)
        sanitized_label = self._sanitize_label(label)
        with self.driver.session(database=self.database) as session:
            session.execute_write(self._create_node_tx, payload, [_model_dump(e) for e in evidences], sanitized_label)

    @staticmethod
    def _create_node_tx(tx, node: Dict, evidences: List[Dict], label: str) -> None:
        label = label.strip() or "MPGNode"
        tx.run(
            f"""
            MERGE (n:{label} {{id: $id}})
            SET n += $node
            """,
            id=node["id"],
            node=node,
        )
        for ev in evidences:
            tx.run(
                """
                MERGE (e:Evidence {id: $eid})
                SET e += $ev
                WITH e
                MATCH (n:{label} {id: $nid})
                MERGE (e)-[:SUPPORTS]->(n)
                """,
                eid=ev["id"],
                ev=ev,
                nid=node["id"],
            )

    def create_edge(self, edge: MPGEdge, evidences: Optional[List[EvidenceItem]] = None) -> None:
        evidences = evidences or []
        rel_type = self._sanitize_rel_type(edge.rel_type)
        payload = _model_dump(edge)
        with self.driver.session(database=self.database) as session:
            session.execute_write(self._create_edge_tx, payload, rel_type, [_model_dump(e) for e in evidences])

    @staticmethod
    def _create_edge_tx(tx, edge: Dict, rel_type: str, evidences: List[Dict]) -> None:
        tx.run(
            f"""
            MATCH (a {{id: $src}}), (b {{id: $dst}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r.strength = $strength,
                r.confidence = $confidence,
                r.reasoning = $reasoning
            """,
            **edge,
        )
        for ev in evidences:
            tx.run(
                f"""
                MERGE (e:Evidence {{id: $eid}})
                SET e += $ev
                WITH e
                MATCH (a {{id: $src}})-[r:{rel_type}]->(b {{id: $dst}})
                MERGE (e)-[:SUPPORTS]->(r)
                """,
                eid=ev["id"],
                ev=ev,
                src=edge["src"],
                dst=edge["dst"],
            )

    def create_evidence(self, evidence: EvidenceItem, target_node_id: Optional[str] = None, label: str = "Evidence") -> None:
        payload = _model_dump(evidence)
        with self.driver.session(database=self.database) as session:
            session.execute_write(self._create_evidence_tx, payload, target_node_id, label)

    @staticmethod
    def _create_evidence_tx(tx, evidence: Dict, target_node_id: Optional[str], label: str) -> None:
        tx.run(
            f"""
            MERGE (e:{label} {{id: $id}})
            SET e += $evidence
            """,
            id=evidence["id"],
            evidence=evidence,
        )
        if target_node_id:
            tx.run(
                """
                MATCH (e {id: $eid}), (n {id: $tid})
                MERGE (e)-[:SUPPORTS]->(n)
                """,
                eid=evidence["id"],
                tid=target_node_id,
            )

    def create_segment_state(self, segment_id: str, state: SegmentState) -> None:
        payload = _model_dump(state)
        payload["segment_id"] = segment_id
        with self.driver.session(database=self.database) as session:
            session.execute_write(self._create_segment_state_tx, payload)

    @staticmethod
    def _create_segment_state_tx(tx, state: Dict) -> None:
        tx.run(
            """
            MATCH (s:Segment {id: $segment_id})
            MERGE (st:SegmentState {id: $id})
            SET st += $state
            MERGE (s)-[:HAS_STATE]->(st)
            """,
            **state,
        )

    def get_graph(self, level: Optional[int] = None) -> nx.DiGraph:
        graph = nx.DiGraph()
        node_query = """
        MATCH (n)
        WHERE (n:MPGNode OR n:Segment) {level_filter}
        RETURN labels(n) AS labels, n AS node
        """
        level_filter = "AND n.level = $level" if level is not None else ""
        with self.driver.session(database=self.database) as session:
            for record in session.run(node_query.format(level_filter=level_filter), level=level):
                data = dict(record["node"])
                node_id = data["id"]
                data["labels"] = record["labels"]
                graph.add_node(node_id, **data)

            edge_query = """
            MATCH (a)-[r]->(b)
            WHERE (a:MPGNode OR a:Segment) AND (b:MPGNode OR b:Segment)
            {level_filter}
            RETURN a.id AS src, b.id AS dst, type(r) AS rel_type, r AS rel
            """
            if level is not None:
                edge_level_filter = "AND a.level = $level AND b.level = $level"
            else:
                edge_level_filter = ""
            for record in session.run(edge_query.format(level_filter=edge_level_filter), level=level):
                rel_props = dict(record["rel"])
                rel_props["rel_type"] = record["rel_type"]
                graph.add_edge(record["src"], record["dst"], **rel_props)
        return graph

    def update_confidence(self, node_id: str, alpha: float = 0.3) -> float:
        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH (n {id: $node_id})<-[:SUPPORTS]-(e:Evidence)
                RETURN e.c AS c, e.q AS q, e.u AS u, e.t AS t
                """,
                node_id=node_id,
            )
            evidence = [
                EvidenceItem(
                    id="",
                    description="",
                    source_type="",
                    pointer="",
                    snippet="",
                    timestamp=0.0,
                    c=row["c"],
                    q=row["q"],
                    u=row["u"],
                    t=row["t"],
                )
                for row in result
            ]
            confidence = self.compute_confidence(evidence, alpha=alpha)
            session.run(
                """
                MATCH (n {id: $node_id})
                SET n.confidence = $confidence, n.updated_at = datetime()
                """,
                node_id=node_id,
                confidence=confidence,
            )
            return confidence

    @staticmethod
    def _sanitize_rel_type(rel_type: str) -> str:
        normalized = rel_type.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_]+", normalized):
            raise ValueError("Relationship types must be alphanumeric with underscores")
        return normalized

    @staticmethod
    def _sanitize_label(label: str) -> str:
        normalized = label.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", normalized):
            raise ValueError("Labels must start with a letter and contain only alphanumerics or underscores")
        return normalized


class InMemoryMPGRepository:
    def __init__(self):
        self.nodes: Dict[str, MPGNode] = {}
        self.edges: List[MPGEdge] = []
        self.evidence_links: Dict[str, List[EvidenceItem]] = {}
        self.segment_states: Dict[str, List[SegmentState]] = {}

    @staticmethod
    def _dump_model(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return obj

    def node_exists(self, node_id: str) -> bool:
        return node_id in self.nodes

    def top_segments(self, limit: int = 5) -> List[Dict]:
        segs = [n for n in self.nodes.values() if n.level >= 1 or "Segment" in n.layers]
        segs_sorted = sorted(segs, key=lambda n: (n.importance, n.confidence), reverse=True)
        return [self._dump_model(n) for n in segs_sorted[:limit]]

    def get_segment_states(self, segment_id: str, limit: int = 5) -> List[Dict]:
        states = self.segment_states.get(segment_id, [])
        sorted_states = sorted(states, key=lambda st: st.t, reverse=True)[:limit]
        return [self._dump_model(s) for s in sorted_states]

    def update_segment_metadata(
        self,
        segment_id: str,
        name: Optional[str] = None,
        importance: Optional[float] = None,
        visible: Optional[bool] = None,
    ) -> None:
        if segment_id not in self.nodes:
            return
        node = self.nodes[segment_id]
        updates = {}
        if name is not None:
            updates["name"] = name
        if importance is not None:
            updates["importance"] = importance
        if visible is not None:
            updates["visible"] = visible
        self.nodes[segment_id] = node.model_copy(update=updates)

    @staticmethod
    def compute_confidence(evidence_items: Iterable[EvidenceItem], alpha: float = 0.3) -> float:
        support = sum(e.c * e.q * e.u * e.t for e in evidence_items)
        return float(1 - math.exp(-alpha * support))

    def create_node(self, node: MPGNode, evidences: Optional[List[EvidenceItem]] = None, label: str = "MPGNode") -> None:
        self.nodes[node.id] = node
        if evidences:
            self.evidence_links[node.id] = evidences

    def create_edge(self, edge: MPGEdge, evidences: Optional[List[EvidenceItem]] = None) -> None:
        if edge.src not in self.nodes or edge.dst not in self.nodes:
            raise ValueError("Both nodes must exist before creating an edge")
        self.edges.append(edge)
        if evidences:
            self.evidence_links[f"{edge.src}->{edge.dst}"] = evidences

    def create_evidence(self, evidence: EvidenceItem, target_node_id: Optional[str] = None, label: str = "Evidence") -> None:
        key = target_node_id or evidence.id
        evs = self.evidence_links.get(key, [])
        evs.append(evidence)
        self.evidence_links[key] = evs
        if target_node_id and target_node_id not in self.nodes:
            # Allow evidence to be stored even if node is missing; caller can reconcile later.
            return

    def create_segment_state(self, segment_id: str, state: SegmentState) -> None:
        states = self.segment_states.get(segment_id, [])
        states.append(state)
        self.segment_states[segment_id] = states

    def get_graph(self, level: Optional[int] = None) -> nx.DiGraph:
        graph = nx.DiGraph()
        for node in self.nodes.values():
            if level is None or node.level == level:
                graph.add_node(node.id, **node.dict())
        for edge in self.edges:
            if level is None:
                graph.add_edge(edge.src, edge.dst, **edge.dict())
            else:
                if self.nodes[edge.src].level == level and self.nodes[edge.dst].level == level:
                    graph.add_edge(edge.src, edge.dst, **edge.dict())
        return graph

    def update_confidence(self, node_id: str, alpha: float = 0.3) -> float:
        evidences = self.evidence_links.get(node_id, [])
        confidence = self.compute_confidence(evidences, alpha=alpha)
        node = self.nodes[node_id]
        self.nodes[node_id] = node.model_copy(update={"confidence": confidence})
        return confidence
