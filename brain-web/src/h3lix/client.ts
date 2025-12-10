import {
  DecisionTraceResponse,
  ReplayResponse,
  SessionSummary,
  SnapshotResponse,
  TelemetryEnvelope,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function listSessions(): Promise<SessionSummary[]> {
  const res = await fetch(`${API_BASE}/v1/sessions`);
  if (!res.ok) throw new Error("Failed to list sessions");
  return res.json();
}

export async function getSnapshot(sessionId: string, tRelMs?: number): Promise<SnapshotResponse> {
  const url = new URL(`${API_BASE}/v1/sessions/${sessionId}/snapshot`, window.location.origin);
  if (tRelMs != null) url.searchParams.set("t_rel_ms", String(tRelMs));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch snapshot");
  return res.json();
}

export async function getReplay(sessionId: string, fromMs: number, toMs: number): Promise<ReplayResponse> {
  const url = new URL(`${API_BASE}/v1/sessions/${sessionId}/replay`, window.location.origin);
  url.searchParams.set("from_ms", String(fromMs));
  url.searchParams.set("to_ms", String(toMs));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch replay");
  return res.json();
}

export async function getDecisionTrace(sessionId: string, decisionId: string): Promise<DecisionTraceResponse> {
  const res = await fetch(`${API_BASE}/v1/sessions/${sessionId}/decisions/${decisionId}`);
  if (!res.ok) throw new Error("Failed to fetch decision trace");
  return res.json();
}

type StreamEvent<TPayload = unknown> = {
  type: "event";
  subscription_id: string;
  data: TelemetryEnvelope<TPayload>;
};

type StreamAck = { type: "ack"; subscription_id: string };
type StreamMessage = StreamEvent | StreamAck;

type StreamOptions = {
  sessionId: string;
  messageTypes: string[];
  onEvent: (event: StreamEvent) => void;
  onClose?: () => void;
};

export function openStream(opts: StreamOptions): WebSocket {
  const ws = new WebSocket(
    `${window.location.origin.replace(/^http/, "ws")}${API_BASE}/v1/stream`,
    "json_v1"
  );
  ws.onopen = () => {
    ws.send(
      JSON.stringify({
        type: "subscribe",
        session_id: opts.sessionId,
        message_types: opts.messageTypes,
      })
    );
  };
  ws.onmessage = (ev) => {
    const msg: StreamMessage = JSON.parse(ev.data);
    if (msg.type === "event") {
      opts.onEvent(msg);
    }
  };
  ws.onclose = () => opts.onClose?.();
  return ws;
}
