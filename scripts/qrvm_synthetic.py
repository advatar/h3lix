"""
Synthetic driver for the Quantum Rogue Variable Module (QRVM).

Creates an in-memory MPG with a few segments, simulates feature overrides,
and runs the QRVManager to demonstrate QMS encoding, Hamiltonian prediction,
and spectral rogue detection + HILD prompts.
"""

from __future__ import annotations

import numpy as np

from core.qrv.manager import QRVManager
from mpg.models import MPGEdge, MPGNode
from mpg.repository import InMemoryMPGRepository


def build_demo_repo() -> InMemoryMPGRepository:
    repo = InMemoryMPGRepository()
    for idx in range(6):
        node = MPGNode(
            id=f"seg_{idx}",
            name=f"Segment {idx}",
            layers=["demo"],
            valence=0.1 * (-1) ** idx,
            intensity=0.4 + 0.05 * idx,
            recency=0.5,
            stability=0.6,
            importance=0.4 + 0.05 * idx,
            confidence=0.5 + 0.05 * idx,
            reasoning="synthetic",
            level=1,
        )
        repo.create_node(node, label="Segment")
    # simple chain of edges
    for idx in range(5):
        repo.create_edge(
            edge=MPGEdge(
                src=f"seg_{idx}",
                dst=f"seg_{idx + 1}",
                rel_type="CAUSES",
                strength=0.6,
                confidence=0.8,
                reasoning="synthetic",
            )
        )
    return repo


def main() -> None:
    repo = build_demo_repo()
    manager = QRVManager(repo, qms_limit=6)
    base = np.zeros(6)
    for step in range(5):
        drift = base.copy()
        drift[step % 6] = 0.4  # induce a rogue-like spike
        result = manager.process_tick(session_id="demo_session", t_rel_ms=step * 1000, feature_overrides=drift)
        detection = result["detection"]
        print(f"t={step}s | triggered={detection.triggered} | rogue_segments={detection.rogue_segments}")
        if detection.triggered:
            hild = result["hild"]
            if hild.prompt:
                print("HILD prompt:", hild.prompt.text)


if __name__ == "__main__":
    main()
