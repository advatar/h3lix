from __future__ import annotations

from typing import Dict, List

import numpy as np

from core.qrv.models import QMSState


class RosettaStoneAligner:
    def __init__(self, noise: float = 0.0):
        self.noise = noise

    def align(self, qms: QMSState) -> Dict:
        vec = np.array(qms.amplitudes, dtype=np.complex128)
        if self.noise > 0:
            vec = vec + self.noise * (np.random.default_rng().standard_normal(vec.shape) * 1j)
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return {
            "basis": qms.basis,
            "aligned_state": vec.tolist(),
            "norm": norm,
        }

    def summarize_group(self, states: List[QMSState]) -> Dict:
        if not states:
            return {"archetypes": []}
        # simple centroid as placeholder
        max_len = max(len(s.amplitudes) for s in states)
        mat = []
        for s in states:
            vec = np.array(s.amplitudes, dtype=np.complex128)
            if vec.size < max_len:
                vec = np.pad(vec, (0, max_len - vec.size))
            mat.append(vec)
        mat = np.vstack(mat)
        centroid = mat.mean(axis=0)
        return {
            "archetypes": [
                {
                    "centroid": centroid.tolist(),
                    "participants": len(states),
                }
            ]
        }
