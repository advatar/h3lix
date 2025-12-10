from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ActionDef:
    id: str
    name: str
    params_template: Dict[str, Any]


class LinearUCBBandit:
    def __init__(self, actions: List[ActionDef], d: int, alpha: float = 1.0):
        self.actions = actions
        self.d = d
        self.alpha = alpha
        self.A = {a.id: np.eye(d) for a in actions}
        self.b = {a.id: np.zeros((d, 1)) for a in actions}

    def _theta(self, aid: str) -> np.ndarray:
        A_inv = np.linalg.inv(self.A[aid])
        return A_inv @ self.b[aid]

    def select_action(self, x: np.ndarray) -> ActionDef:
        x_vec = x.reshape(-1, 1)
        best_val = -np.inf
        best_action = self.actions[0]
        for a in self.actions:
            A_inv = np.linalg.inv(self.A[a.id])
            theta = self._theta(a.id)
            mu = float((theta.T @ x_vec).item())
            ucb = self.alpha * float(np.sqrt((x_vec.T @ A_inv @ x_vec).item()))
            val = mu + ucb
            if val > best_val:
                best_val = val
                best_action = a
        return best_action

    def update(self, x: np.ndarray, aid: str, reward: float) -> None:
        x_vec = x.reshape(-1, 1)
        self.A[aid] += x_vec @ x_vec.T
        self.b[aid] += reward * x_vec
