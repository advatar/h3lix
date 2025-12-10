import asyncio

import numpy as np
import pytest

from core.qrv.manager import QRVManager
from mpg.models import MPGEdge, MPGNode
from mpg.repository import InMemoryMPGRepository


def _build_repo(n_segments: int = 3) -> InMemoryMPGRepository:
    repo = InMemoryMPGRepository()
    for i in range(n_segments):
        repo.create_node(
            MPGNode(
                id=f"seg_{i}",
                name=f"Segment {i}",
                layers=["demo"],
                valence=0.1,
                intensity=0.5,
                recency=0.5,
                stability=0.5,
                importance=0.5,
                confidence=0.5,
                reasoning="test",
                level=1,
            ),
            label="Segment",
        )
    # add a simple edge to avoid empty Hamiltonian
    if n_segments >= 2:
        repo.create_edge(
            MPGEdge(
                src="seg_0",
                dst="seg_1",
                rel_type="CAUSES",
                strength=0.6,
                confidence=0.8,
                reasoning="test",
            )
        )
    return repo


class DummyBus:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def subscribe(self):
        return self.queue

    def unsubscribe(self, queue):
        return

    async def publish(self, message):
        await self.queue.put(message)


def test_qrv_manager_detects_rogue():
    repo = _build_repo()
    manager = QRVManager(repo, qms_limit=3, bus=None)
    manager._last_qms["s1"] = manager.qms_builder.build_from_segments(
        session_id="s1",
        t_rel_ms=0.0,
        limit=3,
        feature_overrides=[0.0, 0.0, 0.0],
    )
    result = manager.process_tick(session_id="s1", t_rel_ms=1000, feature_overrides=np.array([1.0, 0.0, 0.0]))
    detection = result["detection"]
    assert detection is not None
    assert detection.rogue_directions
    assert isinstance(detection.ablation_improvement, float)


def test_hild_ack_resolves():
    bus = None
    repo = _build_repo()
    manager = QRVManager(repo, qms_limit=3, bus=bus)
    # trigger detection and HILD clarifying
    manager.process_tick(session_id="s2", t_rel_ms=0, feature_overrides=np.zeros(3))
    manager.process_tick(session_id="s2", t_rel_ms=1000, feature_overrides=np.array([1.0, 0.0, 0.0]))
    status = manager.acknowledge_prompt(session_id="s2", response="walking", t_rel_ms=1500)
    assert status.state.value == "Resolved"
