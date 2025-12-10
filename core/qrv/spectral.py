from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np

from core.qrv.models import QMSState, RogueDetectionResult, RogueDirection


class SpectralRogueDetector:
    def __init__(
        self,
        max_directions: int = 3,
        loading_top_k: int = 5,
        improvement_tolerance: float = 1e-6,
    ):
        self.max_directions = max_directions
        self.loading_top_k = loading_top_k
        self.improvement_tolerance = improvement_tolerance

    def _error_operator(self, psi_obs: np.ndarray, psi_pred: np.ndarray) -> Tuple[np.ndarray, float]:
        delta = psi_obs - psi_pred
        error_norm = float(np.linalg.norm(delta))
        return np.outer(delta, np.conjugate(delta)), error_norm

    def _top_loadings(self, vec: np.ndarray, basis: Sequence[str]) -> List[str]:
        mags = np.abs(vec)
        sorted_idx = np.argsort(mags)[::-1]
        top_idx = sorted_idx[: self.loading_top_k]
        return [basis[i] for i in top_idx if mags[i] > 0]

    def _ablate(self, psi_obs: np.ndarray, psi_pred: np.ndarray, indices: Iterable[int]) -> float:
        psi_hat = psi_obs.copy()
        for idx in indices:
            if 0 <= idx < psi_hat.size:
                psi_hat[idx] = 0.0
        norm = np.linalg.norm(psi_hat)
        if norm > 0:
            psi_hat = psi_hat / norm
        return float(np.linalg.norm(psi_hat - psi_pred))

    def detect(self, observed: QMSState, predicted: QMSState) -> RogueDetectionResult:
        psi_obs = np.array(observed.amplitudes, dtype=np.complex128)
        psi_pred = np.array(predicted.amplitudes, dtype=np.complex128)

        if psi_obs.size == 0:
            return RogueDetectionResult(
                triggered=False,
                error_norm=0.0,
                ablation_improvement=0.0,
                rogue_directions=[],
                rogue_segments=[],
                pre_state=observed,
                post_state=predicted,
            )

        oe, error_norm = self._error_operator(psi_obs, psi_pred)
        eigvals, eigvecs = np.linalg.eigh(oe)
        order = np.argsort(eigvals)[::-1]
        rogue_dirs: List[RogueDirection] = []
        high_segments: List[str] = []

        for idx in order[: self.max_directions]:
            val = float(eigvals[idx])
            vec = eigvecs[:, idx]
            loads = {basis_id: float(abs(vec[i]) ** 2) for i, basis_id in enumerate(observed.basis)}
            top_segments = self._top_loadings(vec, observed.basis)
            high_segments.extend(top_segments)
            rogue_dirs.append(
                RogueDirection(
                    direction_id=f"chi_{idx}",
                    eigenvalue=val,
                    loadings=loads,
                    high_segments=top_segments,
                    delta_error=0.0,
                )
            )

        unique_high = list(dict.fromkeys(high_segments))
        ablate_indices = [observed.basis.index(seg) for seg in unique_high if seg in observed.basis]
        ablated_error = self._ablate(psi_obs, psi_pred, ablate_indices)
        improvement = ablated_error - error_norm

        for rd in rogue_dirs:
            rd.delta_error = improvement

        triggered = improvement < -self.improvement_tolerance
        return RogueDetectionResult(
            triggered=triggered,
            error_norm=error_norm,
            ablation_improvement=improvement,
            rogue_directions=rogue_dirs,
            rogue_segments=unique_high,
            pre_state=observed,
            post_state=predicted,
        )
