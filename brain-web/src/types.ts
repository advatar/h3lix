export type Position = {
  x: number;
  y: number;
  z: number;
};

export type VisualNode = {
  id: string;
  name: string;
  level: number;
  importance: number;
  confidence: number;
  labels: string[];
  position: Position;
  color: string;
  size: number;
  valence?: number;
};

export type VisualEdge = {
  src: string;
  dst: string;
  rel_type: string;
  strength: number;
  confidence: number;
  color: string;
};

export type GraphSnapshot = {
  level?: number | null;
  layout: string;
  nodes: VisualNode[];
  edges: VisualEdge[];
};

export type EventEnvelope = {
  event_id: string;
  participant_id: string;
  source: string;
  stream_type: string;
  timestamp_utc?: string;
  session_id?: string;
  scope?: string;
  payload?: Record<string, unknown>;
};

export type EventRecord = {
  event: EventEnvelope;
  aligned_timestamp: string;
  received_at: string;
  clock_offset_s?: number;
  drift_ppm?: number;
};

export type EventReceipt = {
  event_id: string;
  participant_id: string;
  source: string;
  stream_type: string;
  aligned_timestamp: string;
  received_at: string;
  clock_offset_s: number;
  drift_ppm: number;
};

export type StreamUpdate = {
  receipt: EventReceipt;
  metrics: Record<string, unknown>;
  aligned_ts_ms?: number;
};

export type BrainSnapshot = {
  graph: GraphSnapshot;
  recent_events: EventRecord[];
};

export type QRVEvent = {
  kind: "qrv_detection" | "hild_status";
  session_id?: string;
  t_rel_ms?: number;
  event_id?: string;
  rogue_segments?: string[];
  error_norm?: number;
  ablation_improvement?: number;
  state?: string;
  prompt?: string | null;
  meta?: Record<string, unknown>;
};

export type BrainEvent = {
  kind: "stream_event" | "graph_snapshot" | "qrv_event";
  stream?: StreamUpdate;
  graph?: GraphSnapshot;
  snapshot?: BrainSnapshot;
  qrv?: QRVEvent;
  meta?: Record<string, unknown>;
};
