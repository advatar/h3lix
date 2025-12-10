"""
Batch alignment job for the Rosetta Stone Layer (RSL).

Reads QRV RogueEvent records from the Parquet audit log and produces
group-level rogue archetypes by averaging aligned QMS states.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from core.qrv.rsl import RosettaStoneAligner


def load_states(audit_path: Path) -> Dict[str, List[np.ndarray]]:
    if not audit_path.exists():
        return {}
    df = pd.read_parquet(audit_path)
    sessions: Dict[str, List[np.ndarray]] = {}
    for _, row in df.iterrows():
        amps = row.get("pre_amplitudes")
        if amps is not None and len(amps) > 0:
            vec = np.array(amps, dtype=np.complex128)
        else:
            segments = [s for s in str(row.get("rogue_segments") or "").split(",") if s]
            vec = np.zeros(len(segments) or 1, dtype=np.complex128)
            if vec.size:
                vec[0] = 1.0
        sessions.setdefault(str(row.session_id), []).append(vec)
    return sessions


def main() -> None:
    audit_path = Path("results/qrvm_rvl.parquet")
    sessions = load_states(audit_path)
    aligner = RosettaStoneAligner()
    archetypes = []
    for sid, vecs in sessions.items():
        if not vecs:
            continue
        stacked = np.stack(vecs)
        centroid = stacked.mean(axis=0)
        archetypes.append({"session_id": sid, "centroid": centroid.tolist(), "count": len(vecs)})
    summary = {"archetypes": archetypes}
    out_path = Path("results/rsl_archetypes.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.Series(summary).to_json(out_path)
    print(f"Wrote {len(archetypes)} archetypes to {out_path}")


if __name__ == "__main__":
    main()
