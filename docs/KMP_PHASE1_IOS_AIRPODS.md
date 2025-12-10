# Phase 1 – KMP iOS (AirPods Pro 3) lab prototype

Goal: ship an iOS-first KMP build that streams real human data into Somatic → Symbolic → Noetic and grows the MPG. Scope is simple journaling, one wearable (AirPods Pro 3 for HR/HRV), and a small set of E1-style decision tasks.

## Assumptions and guardrails
- AirPods Pro 3 expose HR + HRV through HealthKit; if HRV is delayed, we still stream HR plus per-minute SDNN when available.
- iOS only for this phase; Android hooks stay stubbed.
- Lab-sized cohort (N ≈ 5–10), supervised runs; data kept pseudonymous per `participant_id`.
- Use existing EventEnvelope contract (kmp/shared + streams/models.py) and `/streams/events` + `/mobile/*` APIs.

## On-device plan (KMP shared + iOS actual)
- Shared (kmp/shared): reuse EventEnvelope, QueueManager, MobileTrialConfig. Add a small `AirpodsSomaticPayload` helper (channels `hr`, `hrv_sdnn`) and clock helper to fill `deviceClock` with monotonic ticks.
- Transport: QueueManager backed by SQLDelight for offline, Ktor client batches to `/streams/events` every 3–5 seconds, TLS + application-level key per participant.
- AirPods HR/HRV collector (iosMain):
  - Request HealthKit permissions for `heartRate`, `heartRateVariabilitySDNN`, `workoutType`.
  - Start an `HKWorkoutSession` + `HKLiveWorkoutBuilder` scoped to device `HKDevice.model == "AirPods Pro"` (or `productType` contains `AirPodsPro3`).
  - Stream `HKCumulativeQuantitySample` / `HKQuantitySample` into EventEnvelope `somatic` events with `source="ios_airpods_pro3"`; include `quality.samplingRateHz` from delivery cadence and `quality.batteryLevel` if exposed.
- Journaling (shared UI + iosMain bridge): simple text box + mood slider → `streamType=text` EventEnvelope with `payload.text`, optional `payload.mood` and `segments` tags.
- E1-style tasks UI: pull configs from `/mobile/experiments/E1` (falls back to local block), render 2AFC decision prompts, capture RT and choice.
  - Emit two things per trial: (1) `streamType=task` EventEnvelope with reaction time, stimulus id, awareness condition, and segments; (2) POST `/mobile/trial_result` so the human DB is updated.
- Session + consent UX: minimal screen to enter `participant_id`, start session (`/mobile/session`), show scopes and toggles (wearables + journaling).

## Event payload shapes (sent via EventEnvelope)
- Somatic (AirPods):
  ```json
  {
    "trial_id": "E1-001",
    "samples": [
      {"channel": "hr", "value": 78.4, "timestamp_utc": "2025-12-03T18:22:10.123Z"},
      {"channel": "hrv_sdnn", "value": 42.0, "timestamp_utc": "2025-12-03T18:22:10.123Z"}
    ],
    "segments": ["seg-stress"],
    "quality": {"sampling_rate_hz": 1.0, "signal_to_noise": 0.9}
  }
  ```
- Journaling:
  ```json
  {"text": "Felt rushed before the task", "mood": -0.2, "segments": ["seg-stress"]}
  ```
- Task result (E1):
  ```json
  {
    "trial_id": "E1-001",
    "stimulus": "bandit_a_vs_b",
    "choice": "B",
    "rt_ms": 740,
    "awareness_condition": "FULL",
    "intuition_rating": 0.6,
    "segments": ["seg-task-block-1"]
  }
  ```

## Backend alignment (Somatic → MPG → Noetic)
- Treat `source="ios_airpods_pro3"` as a wearables scope in `STREAM_SCOPE_MAP`; default `stream_type="somatic"`.
- Somatic path: `streams.processors.SomaticEventProcessor` already expects `samples`; add HRV channel handling in `SomaticFeatureExtractor` if we want HRV-specific windows (e.g., RMSSD/SDNN aggregation).
- Symbolic path: journaling text flows through `SymbolicEventProcessor` → MPG evidence via `MPGSink`; segment IDs can be provided from the app or auto-tagged per session.
- Noetic path: for this phase compute a cheap coherence score from per-block HRV mean vs task accuracy; send as `feature_matrix` in a `task` or `meta` event if we want backend `NoeticEventProcessor` to process it.
- Mobile APIs: continue to use `/mobile/session` and `/mobile/trial_result` so trials are stored alongside stream events; keep `MOBILE_TRIAL_CONFIG` pointed at a minimal E1 block.

## Lab run flow
1. Create participant_id, record consent scopes (wearables + journaling) in Neo4j or the consent manager.
2. Start session from app (`/mobile/session`), start AirPods HR collection, verify `/streams/recent` shows somatic events.
3. Run E1 task block (≈20–40 trials), keep journaling open between blocks.
4. Verify MPG growth: `:Evidence` items from somatic + text, SegmentState updates (arousal/coherence), trial rows in human DB.

## Build steps (ordered)
1) Wire SQLDelight-backed QueueManager + Ktor client in iosMain; add participant/session store.  
2) Implement AirPods HR/HRV collector and map to `somatic` EventEnvelope payloads; smoke-test against `/streams/simulate` infra locally.  
3) Add journaling screen emitting `text` stream events.  
4) Add E1 task screen consuming `/mobile/experiments/E1` and posting `/mobile/trial_result` + `task` events.  
5) Backend tweaks: register new source in consent map, add HRV windowing, optional simple noetic metric from HRV vs accuracy.  
6) Dry run with 1–2 internal users; inspect Neo4j and `/streams/participant/{id}/recent`; adjust sampling/ batching before broader lab use.
