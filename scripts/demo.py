from __future__ import annotations

import numpy as np

from core.mirror import MirrorCore
from core.models import SomaticSample, Trial
from mpg.models import MPGEdge, MPGNode
from mpg.repository import InMemoryMPGRepository
from mpg.segmentation import lift_level
from noetic.coherence import NoeticAnalyzer
from somatic.processor import SomaticFeatureExtractor
from symbolic.belief import SymbolicEngine


def build_sample_repo() -> InMemoryMPGRepository:
    repo = InMemoryMPGRepository()
    nodes = [
        MPGNode(
            id="n1",
            name="anticipation",
            layers=["Psychological"],
            valence=0.2,
            intensity=0.6,
            recency=0.8,
            stability=0.7,
            importance=0.5,
            confidence=0.5,
            reasoning="Seed node",
            level=0,
        ),
        MPGNode(
            id="n2",
            name="risk awareness",
            layers=["History"],
            valence=-0.1,
            intensity=0.4,
            recency=0.5,
            stability=0.6,
            importance=0.6,
            confidence=0.6,
            reasoning="Seed node",
            level=0,
        ),
        MPGNode(
            id="n3",
            name="goal clarity",
            layers=["Psychological"],
            valence=0.7,
            intensity=0.8,
            recency=0.4,
            stability=0.9,
            importance=0.8,
            confidence=0.7,
            reasoning="Seed node",
            level=0,
        ),
        MPGNode(
            id="n4",
            name="situational stress",
            layers=["Somatic"],
            valence=-0.6,
            intensity=0.7,
            recency=0.9,
            stability=0.3,
            importance=0.7,
            confidence=0.4,
            reasoning="Seed node",
            level=0,
        ),
    ]
    for node in nodes:
        repo.create_node(node)

    edges = [
        MPGEdge(src="n1", dst="n2", rel_type="CONTRADICTS", strength=0.7, confidence=0.6, reasoning="Example"),
        MPGEdge(src="n1", dst="n3", rel_type="SUPPORTS", strength=0.8, confidence=0.7, reasoning="Example"),
        MPGEdge(src="n2", dst="n4", rel_type="CAUSES", strength=0.6, confidence=0.5, reasoning="Example"),
        MPGEdge(src="n4", dst="n3", rel_type="BUFFER", strength=0.65, confidence=0.5, reasoning="Example"),
    ]
    for edge in edges:
        repo.create_edge(edge)

    return repo


def run_demo() -> None:
    repo = build_sample_repo()
    segments = lift_level(repo, level=0, strength_threshold=0.5, min_size=2)
    print(f"Lifted {len(segments)} segments")
    for seg in segments:
        print(f"Segment: {seg.name} ({seg.id}) layers={seg.layers}")

    somatic = SomaticFeatureExtractor()
    symbolic = SymbolicEngine(repo)
    noetic = NoeticAnalyzer()
    mirror = MirrorCore(somatic, symbolic, noetic, repo)

    samples = [
        SomaticSample(user_id="u1", trial_id="t1", timestamp=t, channel="HR", value=60 + t)
        for t in np.linspace(0, 1, num=5)
    ]
    samples += [
        SomaticSample(user_id="u1", trial_id="t1", timestamp=t, channel="EDA", value=0.3 + 0.1 * t)
        for t in np.linspace(0, 1, num=5)
    ]

    trial = Trial(id="t1", user_id="u1", session_id="s1", stimulus_onset=0.0, decision_time=1.0, outcome=1.0)
    feature_matrix = np.array([[0.1, 0.2, 0.3], [0.0, 0.5, 0.4], [0.2, 0.2, 0.1]])

    result = mirror.run_trial(
        stimulus="risk reward stimulus",
        trial=trial,
        samples=samples,
        feature_matrix=feature_matrix,
        entropy=0.5,
        stability=0.7,
        outcome=1.0,
    )

    print(f"Action: {result['action']}, outcome={result['outcome']}, coherence={result['coherence']:.3f}")
    print(f"Rogue variables: {[rv.feature for rv in result['rogue_variables']]}")


if __name__ == "__main__":
    run_demo()
