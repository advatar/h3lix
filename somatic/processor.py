from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np

from core.models import SomaticSample


@dataclass
class SomaticState:
    timestamp: float
    channel: str
    state: float
    innovation: float


class SomaticFeatureExtractor:
    def __init__(self, window_seconds: float = 0.5, step_seconds: float = 0.25):
        self.window = window_seconds
        self.step = step_seconds

    def window_features(self, samples: Iterable[SomaticSample]) -> List[Dict]:
        by_channel: Dict[str, List[SomaticSample]] = {}
        for sample in samples:
            by_channel.setdefault(sample.channel, []).append(sample)

        windows: List[Dict] = []
        for channel, series in by_channel.items():
            series = sorted(series, key=lambda s: s.timestamp)
            timestamps = [s.timestamp for s in series]
            values = np.array([s.value for s in series])
            start_time = timestamps[0] if timestamps else 0.0
            end_time = timestamps[-1] if timestamps else 0.0
            t = start_time
            while t + self.window <= end_time:
                mask = (np.array(timestamps) >= t) & (np.array(timestamps) < t + self.window)
                window_values = values[mask]
                if window_values.size:
                    windows.append(
                        {
                            "channel": channel,
                            "start": t,
                            "end": t + self.window,
                            "mean": float(window_values.mean()),
                            "std": float(window_values.std()),
                            "max": float(window_values.max()),
                            "min": float(window_values.min()),
                        }
                    )
                t += self.step
        return windows

    def kalman_filter(self, samples: Iterable[SomaticSample], process_noise: float = 1e-3, measurement_noise: float = 1e-2) -> List[SomaticState]:
        states: List[SomaticState] = []
        by_channel: Dict[str, List[SomaticSample]] = {}
        for sample in samples:
            by_channel.setdefault(sample.channel, []).append(sample)

        for channel, series in by_channel.items():
            series = sorted(series, key=lambda s: s.timestamp)
            if not series:
                continue
            state_estimate = series[0].value
            estimate_cov = 1.0
            for sample in series:
                predict_cov = estimate_cov + process_noise
                kalman_gain = predict_cov / (predict_cov + measurement_noise)
                innovation = sample.value - state_estimate
                state_estimate = state_estimate + kalman_gain * innovation
                estimate_cov = (1 - kalman_gain) * predict_cov
                states.append(
                    SomaticState(
                        timestamp=sample.timestamp,
                        channel=channel,
                        state=state_estimate,
                        innovation=innovation,
                    )
                )
        return states
