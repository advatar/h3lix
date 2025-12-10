import { BrainEvent, BrainSnapshot, EventRecord } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

type SnapshotParams = {
  participantId?: string;
  level?: number | null;
  eventLimit?: number;
};

export async function fetchSnapshot(params: SnapshotParams = {}): Promise<BrainSnapshot> {
  const url = new URL("/brain/snapshot", API_BASE);
  if (params.participantId) {
    url.searchParams.set("participant_id", params.participantId);
  }
  if (params.level !== undefined && params.level !== null) {
    url.searchParams.set("level", String(params.level));
  }
  if (params.eventLimit !== undefined) {
    url.searchParams.set("event_limit", String(params.eventLimit));
  }
  const resp = await fetch(url.toString());
  if (!resp.ok) {
    throw new Error(`Snapshot request failed: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchRecentEvents(participantId: string, limit = 50): Promise<EventRecord[]> {
  const url = new URL(`/streams/participant/${participantId}/recent`, API_BASE);
  url.searchParams.set("limit", String(limit));
  const resp = await fetch(url.toString());
  if (!resp.ok) {
    throw new Error(`Recent events request failed: ${resp.statusText}`);
  }
  return resp.json();
}

type StreamOptions = {
  participantId?: string;
  sessionId?: string;
  level?: number | null;
  onEvent?: (evt: BrainEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
};

export function openBrainStream(opts: StreamOptions): WebSocket {
  const url = new URL("/brain/stream", API_BASE);
  if (opts.participantId) {
    url.searchParams.set("participant_id", opts.participantId);
  }
  if (opts.sessionId) {
    url.searchParams.set("session_id", opts.sessionId);
  }
  if (opts.level !== undefined && opts.level !== null) {
    url.searchParams.set("level", String(opts.level));
  }
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(url.toString());
  socket.onopen = () => opts.onOpen?.();
  socket.onclose = () => opts.onClose?.();
  socket.onmessage = (ev: MessageEvent) => {
    try {
      const parsed: BrainEvent = JSON.parse(ev.data);
      opts.onEvent?.(parsed);
    } catch (err) {
      console.error("Failed to parse brain stream event", err);
    }
  };
  return socket;
}
