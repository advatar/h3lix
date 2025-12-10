export type MessageType =
  | "somatic_state"
  | "symbolic_state"
  | "noetic_state"
  | "decision_cycle"
  | "mpg_delta"
  | "rogue_variable_event"
  | "mufs_event";

export type SourceLayer = "Somatic" | "Symbolic" | "Noetic" | "MirrorCore" | "MPG";
export type StreamName = "somatic" | "symbolic" | "behavioral" | "external";
export type UnawarenessType = "IU" | "PU";

export type SomaticAnticipatoryMarker = {
  marker_type: "readiness_like" | "phase_locking" | "other";
  lead_time_ms: number;
  confidence: number;
};

export type SomaticStatePayload = {
  t_rel_ms: number;
  window_ms: number;
  features: Record<string, number>;
  innovation?: Record<string, number>;
  covariance_diag?: Record<string, number>;
  global_uncertainty_score?: number;
  change_point: boolean;
  anomaly_score?: number;
  anticipatory_markers: SomaticAnticipatoryMarker[];
};

export type SymbolicBelief = {
  id: string;
  kind: "entity" | "event" | "relation" | "policy";
  label: string;
  description?: string;
  valence?: number;
  intensity?: number;
  recency?: number;
  stability?: number;
  confidence: number;
  importance: number;
};

export type SymbolicPredictionOption = {
  value: string;
  probability: number;
};

export type SymbolicPrediction = {
  id: string;
  target_type: "word" | "event" | "outcome";
  horizon_ms?: number;
  topk: SymbolicPredictionOption[];
  brier_score?: number;
  realized_value?: string;
  realized_error?: number;
};

export type SymbolicUncertaintyRegion = {
  label: string;
  belief_ids: string[];
  comment?: string;
};

export type SymbolicStatePayload = {
  t_rel_ms: number;
  belief_revision_id: string;
  beliefs: SymbolicBelief[];
  predictions: SymbolicPrediction[];
  uncertainty_regions: SymbolicUncertaintyRegion[];
};

export type NoeticStreamCorrelation = {
  stream_x: StreamName;
  stream_y: StreamName;
  r: number;
};

export type NoeticSpectrumBand = {
  band_label: string;
  freq_range_hz: [number, number];
  coherence_strength: number;
};

export type NoeticIntuitiveAccuracyEstimate = {
  p_better_than_baseline: number;
  calibration_error?: number;
};

export type NoeticStatePayload = {
  t_rel_ms: number;
  window_ms: number;
  global_coherence_score: number;
  entropy_change: number;
  stream_correlations: NoeticStreamCorrelation[];
  coherence_spectrum: NoeticSpectrumBand[];
  intuitive_accuracy_estimate?: NoeticIntuitiveAccuracyEstimate;
};

export type DecisionAction = {
  action_id: string;
  label: string;
  params?: Record<string, unknown>;
};

export type DecisionOutcome = {
  label: string;
  metrics: Record<string, number>;
};

export type NoeticAdjustment = {
  attention_gain?: number;
  decision_threshold_delta?: number;
  learning_rate_delta?: number;
};

export type DecisionCyclePayload = {
  sork_cycle_id: string;
  decision_id?: string;
  phase: "S" | "O" | "R" | "K" | "N" | "S_prime";
  phase_started_utc: string;
  phase_ended_utc?: string;
  stimulus_refs?: { channel: string; ref_id: string }[];
  organism_belief_ids?: string[];
  response_action?: DecisionAction;
  consequence_outcome?: DecisionOutcome;
  noetic_adjustments?: NoeticAdjustment;
};

export type MpgEvidencePreview = {
  evidence_id: string;
  snippet: string;
  source_class: string;
  timestamp_utc: string;
};

export type MpgNodeMetrics = {
  valence: number;
  intensity: number;
  recency: number;
  stability: number;
};

export type MpgNode = {
  id: string;
  label: string;
  description?: string;
  layer_tags: string[];
  metrics: MpgNodeMetrics;
  confidence: number;
  importance: number;
  roles: string[];
  evidence_preview: MpgEvidencePreview[];
  reasoning_provenance?: string;
};

export type MpgEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  strength: number;
  confidence: number;
};

export type MpgSegment = {
  id: string;
  label: string;
  level: number;
  member_node_ids: string[];
  cohesion: number;
  average_importance: number;
  average_confidence: number;
  affective_load?: number;
};

export type MpgOperation = {
  kind: "add_node" | "update_node" | "add_edge" | "update_edge" | "add_segment" | "update_segment";
  node?: MpgNode;
  node_id?: string;
  edge?: MpgEdge;
  edge_id?: string;
  segment?: MpgSegment;
  segment_id?: string;
  patch?: Record<string, unknown>;
};

export type MpgDeltaPayload = {
  mpg_id: string;
  level: number;
  delta_id: string;
  operations: MpgOperation[];
};

export type RogueVariableImpactFactors = {
  rate_of_change: number;
  breadth_of_impact: number;
  amplification: number;
  emotional_load: number;
  gate_leverage: number;
  robustness: number;
};

export type RogueVariableShapleyStats = {
  mean_abs_contrib: number;
  std_abs_contrib: number;
  candidate_abs_contrib: number;
  z_score: number;
};

export type RogueVariableEventPayload = {
  rogue_id: string;
  mpg_id: string;
  candidate_type: "segment" | "pathway";
  level_range: [number, number];
  segment_ids?: string[];
  pathway_nodes?: string[];
  shapley_stats: RogueVariableShapleyStats;
  potency_index: number;
  impact_factors: RogueVariableImpactFactors;
};

export type DecisionUtility = {
  choice: string;
  utility: Record<string, number>;
};

export type MufsEventPayload = {
  mufs_id: string;
  decision_id: string;
  mpg_id: string;
  unawareness_types: UnawarenessType[];
  input_unaware_refs?: string[];
  process_unaware_node_ids?: string[];
  decision_full: DecisionUtility;
  decision_without_U: DecisionUtility;
  minimal: boolean;
  search_metadata?: Record<string, unknown>;
};

export type TelemetryEnvelope<TPayload> = {
  v: "1";
  message_type: MessageType;
  timestamp_utc: string;
  experiment_id: string;
  session_id: string;
  subject_id: string;
  run_id?: string;
  sork_cycle_id?: string;
  decision_id?: string;
  source_layer: SourceLayer;
  sequence: number;
  payload: TPayload;
};

export type SessionSummary = {
  session_id: string;
  experiment_id: string;
  subject_id: string;
  status: "active" | "completed" | string;
  started_utc: string;
  ended_utc?: string | null;
};

export type MpgLevelSummary = {
  level: number;
  node_count: number;
  segment_count: number;
};

export type MpgSubgraphResponse = {
  mpg_id: string;
  level: number;
  center_node_id?: string;
  nodes: MpgNode[];
  edges: MpgEdge[];
  segments: MpgSegment[];
};

export type SnapshotMpg = {
  mpg_id: string;
  level_summaries: MpgLevelSummary[];
  base_subgraph: MpgSubgraphResponse;
};

export type SnapshotResponse = {
  session_id: string;
  t_rel_ms: number;
  somatic: SomaticStatePayload;
  symbolic: SymbolicStatePayload;
  noetic: NoeticStatePayload;
  last_decision_cycle?: DecisionCyclePayload;
  mpg: SnapshotMpg;
};

export type ReplayResponse = {
  session_id: string;
  from_ms: number;
  to_ms: number;
  messages: TelemetryEnvelope<unknown>[];
};

export type DecisionTraceResponse = {
  session_id: string;
  decision_id: string;
  phases: DecisionCyclePayload[];
  mufs_events: MufsEventPayload[];
  rogue_variable_events: RogueVariableEventPayload[];
  mpg_full?: MpgSubgraphResponse;
  mpg_without_mufs?: MpgSubgraphResponse;
};
