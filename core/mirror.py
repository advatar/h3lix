from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from core.models import SomaticSample, Trial
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository
from noetic.coherence import NoeticAnalyzer
from noetic.rogue_variables import RogueVariableDetector
from somatic.processor import SomaticFeatureExtractor
from symbolic.belief import SymbolicEngine
from core.qrv.manager import QRVManager


class MirrorCore:
    def __init__(
        self,
        somatic: SomaticFeatureExtractor,
        symbolic: SymbolicEngine,
        noetic: NoeticAnalyzer,
        mpg_repo: Neo4jMPGRepository | InMemoryMPGRepository,
        rv_detector: Optional[RogueVariableDetector] = None,
        qrv_manager: Optional[QRVManager] = None,
    ):
        self.somatic = somatic
        self.symbolic = symbolic
        self.noetic = noetic
        self.mpg_repo = mpg_repo
        self.rv_detector = rv_detector or RogueVariableDetector()
        self.qrv_manager = qrv_manager

    def run_trial(
        self,
        stimulus: str,
        trial: Trial,
        samples: List[SomaticSample],
        feature_matrix: np.ndarray,
        entropy: float,
        stability: float,
        outcome: Optional[float] = None,
    ) -> Dict:
        somatic_windows = self.somatic.window_features(samples)
        somatic_states = self.somatic.kalman_filter(samples)

        belief = self.symbolic.update_beliefs(stimulus, trial)
        action = self.symbolic.choose_action(belief)

        final_outcome = outcome if outcome is not None else 0.0
        belief = self.symbolic.update_with_feedback(belief, final_outcome)

        coherence = self.noetic.compute_coherence(feature_matrix, entropy, stability)

        rv_detection = self.rv_detector.detect(
            shap_values=[state.state for state in somatic_states],
            feature_names=[state.channel for state in somatic_states],
        )

        qrv_output: Dict | None = None
        if self.qrv_manager:
            feature_flat = feature_matrix.mean(axis=0) if feature_matrix.size else np.array([])
            qrv_output = self.qrv_manager.process_tick(
                session_id=trial.session_id,
                t_rel_ms=trial.decision_time,
                feature_overrides=feature_flat,
            )

        return {
            "action": action,
            "outcome": final_outcome,
            "belief": belief,
            "coherence": coherence,
            "somatic_windows": somatic_windows,
            "rogue_variables": rv_detection,
            "qrvm": qrv_output,
        }
