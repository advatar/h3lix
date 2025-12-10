Short version: you wire real humans in by treating **every data source as a time‑stamped event stream**, push those events through **Somatic / Symbolic / Noetic pipelines**, and use them to update the **MPG + SegmentState** objects you already designed. The “edge device” for most of this is a **Kotlin Multiplatform (KMP)** app that talks to wearables and services and streams encrypted events into the LAIZA backend.  [oai_citation:0‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  

I’ll walk through it step‑by‑step.

---

## 1. First principles from the paper

H3LIX + LAIZA already tells us what we need the pipelines to do:

- **Somatic layer**: ingest multi‑channel physiological data, time‑lock it to events, extract features, estimate a state vector ŝ(t) + innovation ε(t).  [oai_citation:1‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
- **Symbolic layer**: keep time‑aligned records of text, speech, behavior, parse into entities/events/relations, and maintain a belief state.  [oai_citation:2‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
- **Noetic layer**: compute coherence metrics across streams (correlation matrices, entropy change, coherence spectra) and feed adjustments back into SORK‑N.  [oai_citation:3‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
- **LAIZA protocol**: “a vast stream of input data encompassing all available data related to the user” plus strict synchronization to a master clock.  [oai_citation:4‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  

So our job is to:

1. Get those streams *from real life* into a **master timeline** per person.
2. Turn them into **features + Evidence items** that update the Mirrored Profile Graph (MPG).  [oai_citation:5‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
3. Do this safely, privately, and with Kotlin Multiplatform as the mobile edge.

---

## 2. Identity, consent & data contracts (non‑negotiable)

Before talking about tech:

1. **Participant identity**
   - Each human gets a **Participant ID** (as in CR‑005) that *never* leaves your system.
   - Real‑world identity (email, phone, etc.) is stored in a separate, locked system or not at all.

2. **Consent + scopes**
   - Each data source is a **scope**: `wearables`, `email`, `messages`, `audio`, `video`, `location`, etc.
   - The user opts in per‑scope; you store this in Neo4j under `(:Participant)-[:ALLOWS_SCOPE {scope:"wearables"}]->(:ScopeConfig)`.

3. **Data contract**
   - Define a unified **event envelope**:

     ```json
     {
       "participant_id": "P123",
       "source": "android_ppg" | "apple_health" | "gmail" | "whatsapp" | "zoom_audio" | ...,
       "stream_type": "somatic" | "text" | "audio" | "video" | "meta",
       "timestamp_utc": "2025-06-21T12:34:56.789Z",
       "local_device_clock": 1234567890,
       "payload": { ... },
       "quality": {
         "sampling_rate_hz": 25,
         "signal_to_noise": 0.8
       }
     }
     ```

   - Every data connector—mobile, desktop, cloud—emits events in this format.

This is how you meet the “digital phenotyping but safe” requirement from the paper.  [oai_citation:6‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  

---

## 3. Kotlin Multiplatform mobile app: the human edge node

All real‑time human interaction flows through a **KMP app** that can run on Android + iOS (and optionally desktop).

### 3.1 KMP architecture

KMP lets you share **business logic** and keep **platform‑specific sensor hooks**:

- `:shared` (Kotlin common):
  - event model (the envelope above),
  - encryption, batching, retry logic,
  - local feature extraction (e.g., simple HRV stats, step counts),
  - config sync (what streams are enabled, sampling rates).
- `:androidApp`:
  - access to sensors, Bluetooth, Android Health Connect, notifications.
- `:iosApp`:
  - access to HealthKit, CoreMotion, Bluetooth, notifications.

Stack ideas (all Kotlin Multiplatform‑friendly):

- Networking: **Ktor** (client) with WebSockets or gRPC‑like streaming.
- Serialization: **kotlinx.serialization**.
- Persistence: **SQLDelight** or a lightweight K/V store for offline buffers.
- Concurrency: **Coroutines**.

### 3.2 What the KMP app actually does

Per user, the app is:

1. **Wearable & phone sensor hub**
   - Pull heart rate / HRV, step count, sleep, etc. from:
     - vendor SDKs **or**
     - OS aggregators (Health Connect / HealthKit).
   - Direct phone sensors:
     - accelerometer/gyroscope (micro‑motion),
     - oculometrics proxies (blink via camera only with consent),
     - microphone for **prosody only** or raw audio (if allowed).

2. **Interaction capture**
   - In‑app journaling / prompts (self‑report, awareness checks from CR‑005).
   - In‑app interventions (nudges, “slow down” prompts from CR‑007).

3. **On‑device preprocessing (Somatic)**
   - Compute short‑window features:
     - HRV metrics (RMSSD, LF/HF), GSR peaks,
     - movement energy, etc.
   - Tag them with **event markers** (stimulus onset, user interaction times).  [oai_citation:7‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  

4. **Streaming to backend**
   - Batch events (e.g., 1–5 s windows) and send via **WebSocket** to a “Somatic Ingest” service.
   - All data encrypted at rest + in transit; configurable upload schedules (live vs delayed).

If a mobile experience is involved at all, this app *is* the gateway into H3LIX.

---

## 4. Connecting wearables

There are two archetypes:

1. **Phone‑tethered wearables** (most watches/bands)
   - Watch → OS health framework → KMP app.
   - KMP app periodically pulls new samples (HR, HRV, steps) and emits events.

2. **Direct BLE devices** (ECG belts, EDA straps, EEG headbands)
   - Platform‑specific code in `androidApp` / `iosApp` uses BLE to subscribe to sensor characteristics.
   - Incoming bytes → parse → timestamp → downsample/aggregate → emit `somatic` events.

Mapping to Somatic layer:

- Raw samples → z(t) features → buffered → **Somatic service** on backend finishes Kalman‑style state estimation for ŝ(t) and innovation ε(t), exactly as in Sec. 3.1.  [oai_citation:8‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  

---

## 5. Email, messaging, and app data

These are mostly **Symbolic** streams; they live off‑device too.

### 5.1 Connectors (backend side)

Rather than doing IMAP/Slack APIs in the phone, build **cloud connectors**:

- `email-ingest`:
  - Connects to Gmail/IMAP with OAuth (per participant).
  - Streams messages as events with metadata + bodies (or summaries).
- `chat-ingest`:
  - Connects to Slack/Teams/WhatsApp Business APIs, etc.
- `calendar-ingest`, `docs-ingest`, etc.

Each connector:

1. Normalizes to the event envelope (source, timestamps).
2. Tags with **participant_id** (mapping from email/account to Participant is stored in your secure mapping).

### 5.2 Symbolic parsing pipeline

A **Symbolic pipeline** service then:

1. Takes a `text` event (email, chat, document snippet).
2. Runs:
   - LLM‑based parsing → entities, events, relations, sentiment.
   - Topic / intent classification.
3. Emits:
   - `Evidence` objects attached to appropriate `:MPGNode` / `:Segment` (traits, relationships, projects, stressors).  [oai_citation:9‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
   - Updates to the Symbolic belief state (LAIZA’s working memory).

Optionally, small summary back to the mobile app: “Here’s what we think happened over the last day.”

---

## 6. Audio & video streams

These feed **both** Somatic (prosody, micro‑motion) and Symbolic (transcripts).

### 6.1 Capture

Sources:

- Mobile app:
  - In‑app recording (diary, task sessions).
- Desktop:
  - Browser extension or OS app capturing microphone/camera during experiments.
- Online platforms:
  - Zoom/Meet recordings (downloaded with permissions).

We recommend:

- **Chunked uploads**: short segments (e.g., 30–60 s) to object storage (S3, GCS).  
- Metadata events in the stream:

  ```json
  {
    "source": "android_audio_mic",
    "stream_type": "audio",
    "timestamp_utc": "...",
    "payload": {
      "uri": "s3://bucket/p123/audio/segment_001.wav",
      "duration_ms": 60000
    }
  }
  ```

### 6.2 Processing

Backend pipeline:

1. **Speech‑to‑text** → Symbolic events:
   - Transcripts → NLP parsing → MPG updates.
2. **Prosody / affect**:
   - Pitch, energy, jitter → Somatic features (arousal, stress).  [oai_citation:10‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
3. **Video**:
   - Pose estimation, facial expression → Somatic cues (posture, micro‑motion).
   - Scene / object detection → symbolic context (meeting, outdoors, etc.).

Again, everything gets time‑stamped and fed into the same master event stream.

---

## 7. Streaming backend & master clock

To honor LAIZA’s “time‑locked” requirement, you need a proper **streaming backbone**.

### 7.1 Message bus

Use a broker (Kafka, Pulsar, or a simpler queue for v1):

- Topic per participant or per modality:
  - `events.somatic.P123`, `events.text.P123`, `events.meta.P123`, etc.
- The KMP app and cloud connectors all **publish** to these topics.

### 7.2 Time alignment

Every event has:

- `timestamp_utc` – from device synced to NTP.
- `local_device_clock` – monotonic tick.
- Optional `session_clock` for specific experiments.

A **Time Alignment service**:

- Reconciles device clock drift.
- Adds **event markers** for:
  - stimuli,
  - responses,
  - self‑reports,
  - interventions.

Now Somatic/ Symbolic / Noetic services can operate on **consistent sliding windows** of events across streams.

---

## 8. Feeding the H3LIX / MPG stack

Everything above is just plumbing. Here’s how it touches H3LIX:

### 8.1 Somatic → `SegmentState` & Evidence

- Somatic service consumes `somatic` events, runs filters → ŝ(t), ε(t).  [oai_citation:11‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
- For each epoch (trial, minute, day):

  - Write **summaries** as `:Evidence` nodes linked to relevant `:Segment` (e.g., “Somatic: high arousal around work email X”).  [oai_citation:12‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
  - Update or append `:SegmentState` snapshots for segments tied to stress, sleep, etc. (CR‑003):

    ```cypher
    (s:Segment)-[:HAS_STATE]->(st:SegmentState {t: epoch})
    SET st.somatic_arousal = ..., st.coherence = ...
    ```

### 8.2 Symbolic → MPG nodes/edges

- Text/audio/video pipelines parse into **events, traits, routines, conflicts**.
- These become:

  - New `:MPGNode` entries (e.g., “project X”, “relationship with Y”).
  - Edges like `:CAUSES`, `:TRIGGERS`, `:CONTRADICTS` between nodes.  [oai_citation:13‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
  - Evidence and reasoning strings attached, as in Definition 1.  [oai_citation:14‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  

- Periodically, you run the **Lift** operator (CR‑001) to re‑segment and update higher levels.  [oai_citation:15‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  

### 8.3 Noetic → coherence metrics

- Noetic service consumes:

  - smooothed ŝ(t),
  - Symbolic belief state changes,
  - performance / outcome metrics (e.g., from task apps).

- It computes:

  - correlation matrices,
  - entropy‑change coefficients,
  - coherence spectra,  
  as in Sec. 3.3.  [oai_citation:16‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  

- Writes coherence back into `:SegmentState`, `:Trial`, and group‑level structures.

### 8.4 SORK‑N feedback & policies

Now that real data flows are in place, everything from CR‑004–CR‑008 can run “for real”:

- **MUFS search** over restricted awareness trials (e.g., certain inputs masked in app).  [oai_citation:17‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
- **RV & Potency** over streaming data (SHAP on real models).  [oai_citation:18‡Symbiotic_human_AI_architecture.pdf](sediment://file_000000000db071f49f637b00e8081106)  
- **Policies** that suggest interventions (change app prompts, slow decisions, etc.) via KMP app.

---

## 9. Putting it all together: staged rollout

This is a lot. I’d stage it:

1. **Phase 1 – Lab prototype with real humans**
   - KMP app with:
     - simple journaling,
     - one wearable (HR/HRV),
     - a couple of tasks (E1‑style decision tasks).
   - Stream into Somatic + Symbolic + Noetic; build MPG from this limited data.

2. **Phase 2 – Add personal digital traces**
   - Email + calendar + chat connectors **for willing internal users**.
   - Audio/video only in controlled sessions.

3. **Phase 3 – Always‑on streaming**
   - More sensors, background logging, light interventions.
   - Tighten privacy, governance, and policy‑learning constraints.

At every stage, keep the **event envelope, time alignment, and KMP app** as the stable backbone. Everything else is “just” more producers/consumers on that backbone.

---

If you’d like, I can next sketch **concrete KMP module layout + example code skeletons** (e.g., shared module for event batching, Android actual for Health Connect integration, iOS actual for HealthKit) and how they talk to a specific Python/Neo4j backend.
