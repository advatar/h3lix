from __future__ import annotations

from typing import List

import numpy as np

from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from core.qrv.models import QMSState


class HamiltonianBuilder:
    def __init__(self, repo: Neo4jMPGRepository | InMemoryMPGRepository, diag_damping: float = 0.1):
        self.repo = repo
        self.diag_damping = diag_damping

    def build(self, basis: List[str], level: int = 1) -> np.ndarray:
        graph = self.repo.get_graph(level=level)
        n = len(basis)
        h = np.zeros((n, n), dtype=np.complex128)
        index = {node_id: i for i, node_id in enumerate(basis)}
        for u, v, data in graph.edges(data=True):
            if u in index and v in index:
                i, j = index[u], index[v]
                strength = float(data.get("strength", 0.0))
                confidence = float(data.get("confidence", 1.0))
                h[i, j] += strength * confidence
        # simple stabilization: diagonal discourages drift
        for i in range(n):
            h[i, i] -= self.diag_damping * np.sum(np.abs(h[i]))
        return h

    def predict(self, prev_state: QMSState, dt: float = 1.0) -> QMSState:
        psi_prev = np.array(prev_state.amplitudes, dtype=np.complex128)
        h = self.build(prev_state.basis, level=1)
        # first-order approximation to exp(-iH dt)
        psi_pred = psi_prev - 1j * dt * (h @ psi_prev)
        norm = float(np.linalg.norm(psi_pred))
        if norm > 0:
            psi_pred = psi_pred / norm
        return QMSState(
            basis=list(prev_state.basis),
            amplitudes=psi_pred.tolist(),
            session_id=prev_state.session_id,
            t_rel_ms=prev_state.t_rel_ms,
            norm=norm,
            meta={"predicted_from": prev_state.t_rel_ms},
        )
