**Change Request: CR‑436 – Quantum Rogue Variable Layer (QRVM, HILD, RVL, RSL)**

---

## 1. Objective

Integrate the quantum-inspired rogue variable workflow from **P2.pdf** and **Quantum-Inspired-Rogue-Variable-Modelling-2.pdf** into the existing H3LIX stack (CR‑001…CR‑009, CR‑006 collective, CR‑005 human integration, CR‑411+ collaboration) by:

1) Adding a **Quantum MPG State (QMS)** representation (Hilbert-space encoding of MPG/Segment states) and **Hamiltonian-based prediction** of state evolution.  
2) Implementing **Rogue Variable detection via spectral error operators** and **ablation-based confirmation** (Δ(S_j) < 0 as the detection criterion).  
3) Formalizing **Human-in-the-Loop Decoherence (HILD)** with auto-safing (suspend autonomy, minimal clarification prompts, passive-safe fallback).  
4) Persisting events in a **Rogue Variable Library (RVL)** with pre/post collapse states, rogue directions, prompts/responses, and model updates.  
5) Standing up a **Rosetta Stone Layer (RSL)** to align rogue patterns across users/groups (federated + DP-aware), leveraging CR‑006 collective MPG.

---

## 2. Scope

### In scope

- New `core/qrv/` module:
  - QMS encoder over `SegmentState`/`MPGNode` metrics.
  - Hamiltonian builder (structure + metric-driven) and short-step propagator.
  - Error operator `O_e` aggregation and spectral rogue-direction extraction.
  - Ablation tester Δ(S_j) that zeroes/attenuates high-loading segments and re-evaluates coherence / prediction error.
- **HILD state machine** in Mirror Core:
  - Trigger policy (sustained rogue flags + instability).
  - Autonomy suspension hook for policy/intent modules.
  - Clarification prompt generator (Context Anchor + Observed Ambiguity + Minimal Direct Request).
  - Non-response handling (retry, then Passive Safe Mode).
- **RVL persistence** (Neo4j + Parquet logs):
  - Entities for RogueEvent, RogueDirection, RogueSegment, Prompt/Response, Pre/Post QMS, Δ(S_j), model deltas.
- **RSL alignment** service:
  - Map individual QMS/RV signatures into a shared reference space.
  - Build group-level rogue clusters on top of CR‑006 CollectiveSegments.
  - Differential-privacy knobs for aggregation/export.
- API + telemetry surfaces:
  - REST/WebSocket endpoints to fetch QMS snapshots, rogue alerts, HILD status, RVL histories, and RSL summaries.
  - Events for KMP/mobile, clinical mode (CR‑106), and director/participant consoles (CR‑411).
- Demo/experiments:
  - Synthetic and replay-mode notebooks/scripts in `experiments/qrvm/` and `scripts/qrvm_*.py`.
  - Benchmarks that compare SHAP-based RV (CR‑002) vs spectral QRVM on the same runs.

### Out of scope

- Quantum hardware/simulation; this is **quantum-inspired linear algebra** only.
- Full production UX; we provide API + event contracts, not full front-ends.
- New sensor modalities beyond what Somatic already supports (reuse existing streams).

---

## 3. Design

### 3.1 QMS encoding (Ψ_map)

- Build a Hilbert-space state vector `|Ψ_t>` over active `Segment` (and optionally `MPGNode`) ids.  
- Amplitudes per segment k:  
  `ψ_k = norm(g(importance, confidence, valence, recency, stability, intensity, noetic_coherence_hint))`  
  where `g` is a weighted map configurable per protocol; normalize `|Ψ_t>` to unit length.  
- Keep a **basis map** (id → index) and allow **mixed states** (store density-like matrices when uncertainty over samples/trials is high).
- Persist `|Ψ_t>`, basis, and normalization metadata per `(session_id, t_rel_ms)` for replay and RSL alignment.

### 3.2 Hamiltonian & prediction

- Construct `H_t` from MPG structure + metrics: adjacency/edge strengths, potency weights, and temporal damping (recent edges weigh more).  
- Provide two propagators:
  - `Ψ_pred = exp(-i H_t Δt) Ψ_{t-1}` (use truncated series / scaling-squaring for small Δt).
  - A lightweight Euler fallback for real-time tick updates.  
- Log both predicted and observed QMS to compute divergence.

### 3.3 Error operator & rogue directions

- Error residual: `δ_t = Ψ_obs - Ψ_pred`.  
- Error operator: `O_e = δ_t δ_t^†` (optionally accumulated with forgetting factor λ).  
- Spectral step: eigen-decompose `O_e` → rogue directions `{ |χ_j> }` sorted by eigenvalue λ_j.  
- High-loading segments per direction: top-k components by |χ_j|; define candidate sets `S_j`.  
- **Ablation test Δ(S_j):**
  - Zero/attenuate amplitudes for S_j in Ψ_obs → Ψ̂.  
  - Recompute prediction error/coherence; Δ = error(Ψ̂) − error(Ψ_obs).  
  - Rogue condition when Δ < 0 across a smoothing window (and stability < τ).  
- Tag implicated segments with `rv=true`, `rv_score = λ_j`, `rv_source = "qrvm_spectral"`, alongside existing SHAP RV flags (do not overwrite CR‑002 fields; add source-specific namespace).

### 3.4 HILD state machine

- States: `Idle → PendingRogue → Clarifying → PassiveSafe → Resolved`.  
- **Triggers:** rogue condition + instability + unmet confidence threshold (reuse Noetic coherence + MUFS markers as guardrails).  
- **While Clarifying:** disable policy/intent/autonomy modules (CR‑007 interventions pause), keep ingestion running, surface prompts to clients.  
- **Prompt template:** Context Anchor (observable), Observed Ambiguity (mechanical divergence), Minimal Direct Request (single missing variable).  
- **Non-response:** retry once; if silent, enter Passive Safe Mode (no autonomous actions, log unresolved RV event).  
- **Resolution:** apply user response to update node/segment metrics, rebuild `|Ψ_t'>`, clear rogue direction, resume autonomy.

### 3.5 Rogue Variable Library (RVL)

- Neo4j schema (new labels):
  - `:RogueEvent {id, session_id, t_rel_ms, status, trigger, source}`  
  - `:RogueDirection {id, eigenvalue, basis_ids, loadings}`  
  - `:RogueSegment {id, segment_id, loading, delta}`  
  - `:DecoherencePrompt {id, text, anchor, ambiguity, request, responded}`  
  - Relationships: `(:RogueEvent)-[:HAS_DIRECTION]->(:RogueDirection)`, `(:RogueDirection)-[:INVOLVES]->(:Segment)`, `(:RogueEvent)-[:USED_PROMPT]->(:DecoherencePrompt)`, `(:RogueEvent)-[:HAS_PRE_STATE]->(:QMSState)`, `(:RogueEvent)-[:HAS_POST_STATE]->(:QMSState)`.  
- Parquet/JSON audit log mirrors Neo4j entries for offline analysis and DP-safe export.
- Include Δ(S_j), pre/post coherence, and any model parameter updates (H_t adjustments).

### 3.6 Rosetta Stone Layer (RSL)

- Build on CR‑006 CollectiveSegments:
  - Align individual QMS bases into a **reference basis** via learned alignment operators `T_u` (per user u).  
  - Map rogue directions `|χ_j>` into reference space; cluster across users → **Group Rogue Patterns**.  
  - Attach group patterns to `CollectiveSegment` nodes, store `rv_group_score`, `shared_precursor_markers`.  
- Privacy knobs:
  - DP noise on exported loadings/eigenvalues.
  - Optional federated aggregation with per-site clipping.  
- API endpoints to fetch:
  - Per-user → reference alignment quality.
  - Top group rogue archetypes + participant counts.
  - Early-warning markers derived from shared rogue patterns.

### 3.7 API / events / gating

- REST:
  - `GET /qrv/state/{session_id}?t_rel_ms=` → Ψ, H, rogue flags.  
  - `POST /qrv/hild/ack` for user responses; `POST /qrv/hild/override` for clinician/director commands.  
  - `GET /qrv/rvl/{session_id}` → rogue events timeline.  
  - `GET /qrv/rsl/{group_id}` → group rogue archetypes.  
- WebSockets:
  - `qrv/alerts` stream (rogue detected, HILD state changes).
  - `qrv/hild/prompts` stream for client UIs (Vision Pro, web, KMP app).  
- Gating:
  - Respect Clinical Mode roles (CR‑106) and Collaboration roles (CR‑411) for who can respond/override.
  - Default to **assistive**; no automatic interventions during HILD.

### 3.8 Experiments & benchmarks

- `scripts/qrvm_synthetic.py`: simulate MPG/Segment dynamics, induce rogue regimes, compare detection latency vs SHAP RV (CR‑002).  
- `experiments/qrvm_replay.ipynb`: replay recorded sessions, visualize Ψ_pred vs Ψ_obs, λ_j spectra, Δ(S_j), and HILD timings.  
- `experiments/rsl_alignment.ipynb`: evaluate alignment quality and group rogue clusters using multi-user data from CR‑006 demos.  
- Metrics: time-to-detect, false positives vs SHAP RV, user burden (prompt count), time-to-resolve, impact on Noetic coherence and MUFS stability.

---

## 4. Implementation checklist

- [ ] Add `core/qrv/` module with QMS encoder, Hamiltonian builder, spectral detector, ablation tester.  
- [ ] Extend Neo4j schema migrations for RVL + QMSState nodes; add Parquet audit writer.  
- [ ] Wire Mirror Core loop to call QRVM detector each tick and gate autonomy via HILD state machine.  
- [ ] Update API service with QRVM/HILD/RVL/RSL endpoints + WebSocket channels; add role checks.  
- [ ] Build alignment + clustering job for RSL using CR‑006 collective data model.  
- [ ] Add synthetic/replay experiments and CI smoke tests (numerical sanity, schema migrations).  
- [ ] Update docs (CLI usage, API reference, safety notes) and add sample prompts for HILD.

---

## 5. Acceptance criteria

- QMS and Hamiltonian prediction run in real time on existing MPG state; rogue directions are reproducible from the same inputs.  
- Rogue events only fire when ablation improves coherence/error (Δ(S_j) < 0), and segments are flagged without overwriting SHAP RV fields.  
- HILD reliably suspends autonomy, emits prompts, handles retries/passive-safe, and resumes after clarification.  
- RVL entries include pre/post QMS, rogue directions, prompts/responses, Δ(S_j), and model updates; retrieval works via API.  
- RSL produces cross-user/group rogue archetypes on top of CollectiveSegments with DP toggles; endpoints stream summaries without leaking per-user raw data.  
- Existing CR‑002/CR‑006/CR‑005 flows continue to function (no regression in API contracts, schema, or clinical/collab gating).
