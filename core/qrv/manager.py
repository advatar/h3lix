from __future__ import annotations

import asyncio
import uuid
from typing import Dict, Optional, Sequence

import numpy as np

from core.qrv.hamiltonian import HamiltonianBuilder
from core.qrv.hild import HILDStateMachine
from core.qrv.models import HILDStatus, QMSState, RogueDetectionResult, RogueEventRecord
from core.qrv.qms import QMSBuilder
from core.qrv.rsl import RosettaStoneAligner
from core.qrv.rvl import RogueVariableLibrary
from core.qrv.spectral import SpectralRogueDetector
from mpg.repository import InMemoryMPGRepository, Neo4jMPGRepository


class QRVManager:
    def __init__(
        self,
        repo: Neo4jMPGRepository | InMemoryMPGRepository,
        qms_limit: int = 64,
        bus: object | None = None,
    ):
        self.repo = repo
        self.qms_builder = QMSBuilder(repo)
        self.hamiltonian = HamiltonianBuilder(repo)
        self.detector = SpectralRogueDetector()
        self.hild = HILDStateMachine()
        self.rvl = RogueVariableLibrary(repo)
        self.rsl = RosettaStoneAligner()
        self.qms_limit = qms_limit
        self._last_qms: Dict[str, QMSState] = {}
        self.bus = bus

    def process_tick(
        self,
        session_id: str,
        t_rel_ms: float,
        feature_overrides: Sequence[float] | None = None,
    ) -> Dict:
        observed = self.qms_builder.build_from_segments(
            session_id=session_id,
            t_rel_ms=t_rel_ms,
            limit=self.qms_limit,
            feature_overrides=feature_overrides,
        )

        prev = self._last_qms.get(session_id, observed)
        predicted = self.hamiltonian.predict(prev, dt=max((t_rel_ms - (prev.t_rel_ms or t_rel_ms)), 1.0) / 1000.0)

        detection = self.detector.detect(observed, predicted)
        event_id: Optional[str] = None
        if detection.triggered:
            event_id = str(uuid.uuid4())
            detection.event_id = event_id
            record = RogueEventRecord(
                id=event_id,
                session_id=session_id,
                t_rel_ms=t_rel_ms,
                detection=detection,
            )
            self.rvl.record(record)
            self._publish_event(
                {
                    "kind": "qrv_detection",
                    "session_id": session_id,
                    "t_rel_ms": t_rel_ms,
                    "event_id": event_id,
                    "rogue_segments": detection.rogue_segments,
                    "error_norm": detection.error_norm,
                    "ablation_improvement": detection.ablation_improvement,
                }
            )

        status: HILDStatus = self.hild.on_tick(session_id, t_rel_ms, detection)
        self._publish_event(
            {
                "kind": "hild_status",
                "session_id": session_id,
                "t_rel_ms": t_rel_ms,
                "state": status.state.value,
                "prompt": status.prompt.text if status.prompt else None,
            }
        )

        self._last_qms[session_id] = observed

        return {
            "qms_observed": observed,
            "qms_predicted": predicted,
            "detection": detection,
            "hild": status,
            "aligned": self.rsl.align(observed),
            "event_id": event_id,
        }

    def acknowledge_prompt(self, session_id: str, response: str, t_rel_ms: float) -> HILDStatus:
        return self.hild.acknowledge(session_id, response=response, t_rel_ms=t_rel_ms)

    def list_events(self, session_id: Optional[str] = None) -> Dict:
        return {"events": self.rvl.list_events(session_id=session_id)}

    def status(self, session_id: str) -> HILDStatus:
        return self.hild.get_status(session_id)

    def _publish_event(self, message: Dict) -> None:
        if not self.bus:
            return
        # ensure meta for downstream filters
        meta = message.get("meta", {}) if isinstance(message, dict) else {}
        meta.setdefault("session_id", message.get("session_id"))
        message["meta"] = meta
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            loop.create_task(self.bus.publish(message))
        else:
            loop = loop or asyncio.new_event_loop()
            try:
                loop.run_until_complete(self.bus.publish(message))
            finally:
                if not loop.is_running():
                    loop.close()
