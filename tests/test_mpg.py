import networkx as nx

from mpg.models import MPGNode, MPGEdge
from mpg.repository import InMemoryMPGRepository
from mpg.segmentation import segment_graph


def test_segment_graph_groups_strong_edges():
    repo = InMemoryMPGRepository()
    nodes = [
        MPGNode(id="n1", name="a", layers=["L"], valence=0, intensity=0.5, recency=0.5, stability=0.5, importance=0.5, confidence=0.5, reasoning="", level=0),
        MPGNode(id="n2", name="b", layers=["L"], valence=0, intensity=0.5, recency=0.5, stability=0.5, importance=0.5, confidence=0.5, reasoning="", level=0),
        MPGNode(id="n3", name="c", layers=["L"], valence=0, intensity=0.5, recency=0.5, stability=0.5, importance=0.5, confidence=0.5, reasoning="", level=0),
        MPGNode(id="n4", name="d", layers=["L"], valence=0, intensity=0.5, recency=0.5, stability=0.5, importance=0.5, confidence=0.5, reasoning="", level=0),
    ]
    for n in nodes:
        repo.create_node(n)
    edges = [
        MPGEdge(src="n1", dst="n2", rel_type="LINK", strength=0.8, confidence=0.5, reasoning=""),
        MPGEdge(src="n2", dst="n3", rel_type="LINK", strength=0.9, confidence=0.5, reasoning=""),
        MPGEdge(src="n3", dst="n4", rel_type="LINK", strength=0.4, confidence=0.5, reasoning=""),
    ]
    for e in edges:
        repo.create_edge(e)
    graph = repo.get_graph(level=0)
    segments = segment_graph(graph, strength_threshold=0.6, min_size=2)
    assert any({"n1", "n2", "n3"} == set(seg) for seg in segments)
