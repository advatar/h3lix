#!/usr/bin/env python3
"""
Ingest Apple HealthKit export data into the H3lix streaming API.

Usage:
    python3 scripts/ingest_healthkit.py /path/to/export.xml \
        --api http://localhost:8000 --participant demo-user --session demo-session

The script:
  - Ensures consent for the participant (wearables scope).
  - Parses the HealthKit export (plain export.xml or export.zip).
  - Maps common quantity types to somatic stream samples.
  - Sends batched POSTs to /streams/events.
"""

from __future__ import annotations

import argparse
import math
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import requests

# Minimal mapping of HealthKit quantity types to channels
HK_TYPE_MAP: Dict[str, str] = {
    "HKQuantityTypeIdentifierHeartRate": "heart_rate_bpm",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr_bpm",
    "HKQuantityTypeIdentifierRespiratoryRate": "resp_rate_bpm",
    "HKQuantityTypeIdentifierOxygenSaturation": "spo2_pct",
    "HKQuantityTypeIdentifierStepCount": "step_count",
    "HKQuantityTypeIdentifierDistanceWalkingRunning": "distance_m",
    "HKQuantityTypeIdentifierDistanceCycling": "distance_cycling_m",
    "HKQuantityTypeIdentifierBasalEnergyBurned": "basal_energy_kcal",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy_kcal",
}


def parse_iso(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def iter_records(path: str) -> Iterable[Dict[str, object]]:
    def _iter_file(file_obj):
        for _, elem in ET.iterparse(file_obj):
            if elem.tag != "Record":
                elem.clear()
                continue
            hk_type = elem.attrib.get("type") or ""
            channel = HK_TYPE_MAP.get(hk_type)
            if not channel:
                elem.clear()
                continue
            raw_val = elem.attrib.get("value")
            if raw_val is None:
                elem.clear()
                continue
            try:
                value = float(raw_val)
            except ValueError:
                elem.clear()
                continue
            if not math.isfinite(value):
                elem.clear()
                continue
            ts = elem.attrib.get("startDate") or elem.attrib.get("creationDate") or elem.attrib.get("endDate")
            if not ts:
                elem.clear()
                continue
            dt = parse_iso(ts)
            yield {"channel": channel, "value": value, "timestamp_utc": dt.isoformat()}
            elem.clear()

    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            with zf.open("export.xml") as f:
                yield from _iter_file(f)
    else:
        with open(path, "rb") as f:
            yield from _iter_file(f)


def post_consent(api_base: str, participant_id: str) -> None:
    url = f"{api_base.rstrip('/')}/consent/participant"
    resp = requests.post(url, json={"participant_id": participant_id, "scopes": ["wearables"]}, timeout=30)
    resp.raise_for_status()


def send_batches(
    api_base: str,
    participant_id: str,
    session_id: str,
    records: Iterable[Dict[str, object]],
    batch_size: int = 200,
) -> int:
    url = f"{api_base.rstrip('/')}/streams/events"
    batch: List[Dict[str, object]] = []
    sent = 0
    for rec in records:
        batch.append(
            {
                "participant_id": participant_id,
                "source": "healthkit",
                "stream_type": "somatic",
                "timestamp_utc": rec["timestamp_utc"],
                "session_id": session_id,
                "payload": {"samples": [rec]},
            }
        )
        if len(batch) >= batch_size:
            resp = requests.post(url, json={"events": batch}, timeout=60)
            resp.raise_for_status()
            sent += len(batch)
            batch = []
    if batch:
        resp = requests.post(url, json={"events": batch}, timeout=60)
        resp.raise_for_status()
        sent += len(batch)
    return sent


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest HealthKit export into H3lix API.")
    parser.add_argument("export_path", help="Path to Apple Health export.xml or export.zip")
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--participant", default="healthkit-user", help="Participant ID to use")
    parser.add_argument("--session", default="healthkit-session", help="Session ID to use")
    parser.add_argument("--batch", type=int, default=200, help="Batch size for POST /streams/events")
    args = parser.parse_args(argv)

    try:
        post_consent(args.api, args.participant)
    except Exception as exc:
        print(f"Failed to set consent: {exc}", file=sys.stderr)
        return 1

    try:
        records = list(iter_records(args.export_path))
    except FileNotFoundError:
        print(f"Export not found: {args.export_path}", file=sys.stderr)
        return 1
    except zipfile.BadZipFile:
        print(f"Invalid zip file: {args.export_path}", file=sys.stderr)
        return 1

    if not records:
        print("No HealthKit records parsed; check the export file.", file=sys.stderr)
        return 1

    try:
        sent = send_batches(args.api, args.participant, args.session, records, batch_size=args.batch)
    except Exception as exc:
        print(f"Ingest failed after sending {sent if 'sent' in locals() else 0} events: {exc}", file=sys.stderr)
        return 1

    print(f"Ingest complete: {sent} events sent for participant '{args.participant}' session '{args.session}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
