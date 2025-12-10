import { useEffect, useMemo, useRef, useState } from "react";
import { fetchRecentEvents, fetchSnapshot, openBrainStream } from "./api/client";
import { BrainScene } from "./scene/BrainScene";
import { useBrainStore } from "./state/useBrainStore";
import { BrainEvent, EventRecord, StreamUpdate, QRVEvent } from "./types";
import "./styles.css";

const formatTime = (iso?: string) => {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleTimeString(undefined, { hour12: false });
};

const formatMs = (ms?: number) => {
  if (!ms) return "";
  return formatTime(new Date(ms).toISOString());
};

function useBrainController() {
  const { setSnapshot, pushStreamUpdate, setConnected, setConnecting, clearLive, addQRVEvent } = useBrainStore();
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const handleEvent = (evt: BrainEvent) => {
    if (evt.kind === "graph_snapshot" && evt.snapshot) {
      setSnapshot(evt.snapshot);
    }
    if (evt.kind === "stream_event" && evt.stream) {
      pushStreamUpdate(evt.stream);
    }
    if (evt.kind === "qrv_event" && evt.qrv) {
      addQRVEvent(evt.qrv as QRVEvent);
    }
  };

  const connect = (participantId?: string, level?: number | null) => {
    clearLive();
    setConnecting(true);
    socketRef.current?.close();
    socketRef.current = openBrainStream({
      participantId,
      level,
      onEvent: handleEvent,
      onOpen: () => {
        setError(null);
        setConnected(true);
        setConnecting(false);
      },
      onClose: () => {
        setConnected(false);
        setConnecting(false);
      },
    });
  };

  const disconnect = () => {
    socketRef.current?.close();
    setConnected(false);
  };

  const loadSnapshot = async (participantId?: string, level?: number | null) => {
    try {
      setError(null);
      const snap = await fetchSnapshot({ participantId, level, eventLimit: 40 });
      setSnapshot(snap);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Snapshot failed");
    }
  };

  useEffect(() => {
    return () => socketRef.current?.close();
  }, []);

  return { connect, disconnect, loadSnapshot, error };
}

export default function App() {
  const {
    nodes,
    edges,
    liveStream,
    qrvEvents,
    recentEvents,
    connected,
    connecting,
    selectedNodeId,
    setSelectedNode,
    pushStreamUpdate,
  } = useBrainStore();
  const [participantId, setParticipantId] = useState("");
  const [levelInput, setLevelInput] = useState<string>("");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [playbackEvents, setPlaybackEvents] = useState<EventRecord[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const playbackIdx = useRef(0);
  const { connect, loadSnapshot, error } = useBrainController();
  const playbackTimer = useRef<number | null>(null);

  const parsedLevel = useMemo(() => {
    if (!levelInput.trim()) return null;
    const n = Number(levelInput);
    return Number.isFinite(n) ? n : null;
  }, [levelInput]);

  useEffect(() => {
    loadSnapshot(participantId || undefined, parsedLevel);
    connect(participantId || undefined, parsedLevel);
    setLastRefresh(new Date());
  }, [participantId, parsedLevel]);

  const handleRefresh = async () => {
    await loadSnapshot(participantId || undefined, parsedLevel);
    setLastRefresh(new Date());
  };

  const handleLoadHistory = async () => {
    if (!participantId) return;
    try {
      const events = await fetchRecentEvents(participantId, 120);
      const sorted = [...events].sort(
        (a, b) => new Date(a.aligned_timestamp).getTime() - new Date(b.aligned_timestamp).getTime(),
      );
      setPlaybackEvents(sorted);
    } catch (err) {
      console.error(err);
    }
  };

  const renderQRV = () => {
    if (!qrvEvents.length) return null;
    const latest = qrvEvents[0];
    return (
      <div className="panel">
        <div className="panel-title">QRV / HILD</div>
        <div className="panel-body">
          <div><strong>State:</strong> {latest.state || "rogue"}</div>
          <div><strong>Rogue Segments:</strong> {(latest.rogue_segments || []).join(", ") || "n/a"}</div>
          <div><strong>Error Norm:</strong> {latest.error_norm?.toFixed(3) ?? "-"}</div>
          <div><strong>Prompt:</strong> {latest.prompt || "—"}</div>
        </div>
      </div>
    );
  };

  const stopPlayback = () => {
    if (playbackTimer.current) {
      clearTimeout(playbackTimer.current);
    }
    playbackTimer.current = null;
    setIsPlaying(false);
    playbackIdx.current = 0;
  };

  const toStreamUpdate = (evt: EventRecord): StreamUpdate => ({
    receipt: {
      event_id: evt.event.event_id,
      participant_id: evt.event.participant_id,
      source: evt.event.source,
      stream_type: evt.event.stream_type,
      aligned_timestamp: evt.aligned_timestamp,
      received_at: evt.received_at,
      clock_offset_s: evt.clock_offset_s ?? 0,
      drift_ppm: evt.drift_ppm ?? 0,
    },
    metrics: evt.event.payload || {},
    aligned_ts_ms: new Date(evt.aligned_timestamp).getTime(),
  });

  useEffect(() => {
    if (!isPlaying || playbackEvents.length === 0) return;
    playbackIdx.current = 0;

    const scheduleNext = (idx: number) => {
      const evt = playbackEvents[idx];
      if (!evt) {
        stopPlayback();
        return;
      }
      const prevTs =
        idx === 0
          ? new Date(playbackEvents[0].aligned_timestamp).getTime()
          : new Date(playbackEvents[idx - 1].aligned_timestamp).getTime();
      const ts = new Date(evt.aligned_timestamp).getTime();
      const delay = Math.max(0, ts - prevTs);
      playbackTimer.current = window.setTimeout(() => {
        pushStreamUpdate(toStreamUpdate(evt));
        scheduleNext(idx + 1);
      }, Math.min(delay, 2000));
    };

    scheduleNext(0);
    return stopPlayback;
  }, [isPlaying, playbackEvents, pushStreamUpdate]);

  const totalEvents = liveStream.length + recentEvents.length;
  const selectedNode = useMemo(() => nodes.find((n) => n.id === selectedNodeId) || null, [nodes, selectedNodeId]);
  const connectedEdges = useMemo(
    () => edges.filter((e) => selectedNodeId && (e.src === selectedNodeId || e.dst === selectedNodeId)),
    [edges, selectedNodeId],
  );

  return (
    <div className="app-shell">
      <header className="header">
        <div className="title">
          <div className="status-pill">
            <span className="status-dot" />
            {connected ? "LIVE" : connecting ? "CONNECTING" : "IDLE"}
          </div>
          <div>
            <strong>H3LIX Brain Viewer</strong>
            <div style={{ color: "#8fa1c7", fontSize: 13 }}>Minimum viable brain / web 3D</div>
          </div>
        </div>
        <div className="controls">
          <div className="control">
            <label>Participant</label>
            <input
              placeholder="participant id (optional)"
              value={participantId}
              onChange={(e) => setParticipantId(e.target.value)}
            />
          </div>
          <div className="control">
            <label>MPG Level</label>
            <input
              placeholder="e.g. 0 or 1"
              value={levelInput}
              onChange={(e) => setLevelInput(e.target.value)}
            />
          </div>
          <button className="btn" onClick={handleRefresh}>
            Refresh snapshot
          </button>
          <button className="btn secondary" onClick={handleLoadHistory} disabled={!participantId}>
            Load history
          </button>
        </div>
      </header>

      <div className="canvas-wrap">
        <BrainScene nodes={nodes} edges={edges} selectedId={selectedNodeId} onSelect={setSelectedNode} />
      </div>

      <aside className="side-panel">
        <div className="section-title">Live Stream</div>
        <div className="panel-card">
          <div className="metrics">
            <div className="metric-pill">Nodes: {nodes.length}</div>
            <div className="metric-pill">Edges: {edges.length}</div>
            <div className="metric-pill">Events: {totalEvents}</div>
            {lastRefresh && <div className="metric-pill">Refreshed: {formatTime(lastRefresh.toISOString())}</div>}
          </div>
          {error && <div style={{ color: "#ff9f9f", marginTop: 8 }}>⚠️ {error}</div>}
          <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              className="btn secondary"
              disabled={!participantId || playbackEvents.length === 0}
              onClick={() => setIsPlaying((p) => !p)}
            >
              {isPlaying ? "Stop playback" : "Play history"}
            </button>
            <small style={{ color: "#8fa1c7" }}>
              Playback uses /streams recent events {playbackEvents.length ? `(${playbackEvents.length})` : ""}
            </small>
          </div>
        </div>

        {qrvEvents.length > 0 && (
          <>
            <div className="section-title">QRV / HILD</div>
            <div className="panel-card">
              {qrvEvents.slice(0, 5).map((evt, idx) => (
                <div key={idx} className="metric-pill" style={{ display: "block", alignItems: "flex-start" }}>
                  <div><strong>{evt.state || evt.kind}</strong> @ {evt.t_rel_ms ?? "-"} ms</div>
                  <div style={{ fontSize: 12, color: "#b7c5e5" }}>
                    Segs: {(evt.rogue_segments || []).join(", ") || "n/a"} | Err: {evt.error_norm ?? "-"}
                  </div>
                  {evt.prompt && <div style={{ fontSize: 12, color: "#9ad5ff" }}>Prompt: {evt.prompt}</div>}
                </div>
              ))}
            </div>
          </>
        )}

        <div className="section-title">Legend</div>
        <div className="panel-card">
          <div className="legend">
            <div className="legend-item">
              <span className="legend-swatch" style={{ background: "#3df4ff" }} />
              Confidence ↑
            </div>
            <div className="legend-item">
              <span className="legend-swatch" style={{ background: "#ff7a5c" }} />
              Valence → warm
            </div>
            <div className="legend-item">
              <span className="legend-swatch" style={{ background: "#8fa1c7" }} />
              Link strength
            </div>
          </div>
        </div>

        <div className="section-title">Selection</div>
        <div className="panel-card">
          {selectedNode ? (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{selectedNode.name}</strong>
                <span className="badge">Level {selectedNode.level}</span>
              </div>
              <div className="metrics" style={{ marginTop: 8 }}>
                <div className="metric-pill">Importance: {selectedNode.importance.toFixed(3)}</div>
                <div className="metric-pill">Confidence: {selectedNode.confidence.toFixed(3)}</div>
                {selectedNode.valence !== undefined && (
                  <div className="metric-pill">Valence: {selectedNode.valence?.toFixed(3)}</div>
                )}
              </div>
              <div style={{ marginTop: 8, color: "#b7c5e5", fontSize: 12 }}>
                {selectedNode.labels.join(" • ") || "No labels"}
              </div>
              {connectedEdges.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div className="section-title" style={{ marginBottom: 4 }}>
                    Connected edges
                  </div>
                  <div className="metrics">
                    {connectedEdges.slice(0, 8).map((e) => (
                      <div key={`${e.src}-${e.dst}-${e.rel_type}`} className="metric-pill">
                        {e.rel_type}: {e.src === selectedNode.id ? "→" : "←"} {e.src === selectedNode.id ? e.dst : e.src}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{ color: "#8fa1c7" }}>Click a node to inspect importance/links.</div>
          )}
        </div>

        <div className="section-title">Recent events</div>
        <div className="event-feed">
          {liveStream.map((evt, idx) => {
            const ts = evt.aligned_ts_ms ? formatMs(evt.aligned_ts_ms) : formatTime(evt.receipt.received_at);
            return (
            <div className="event" key={`${evt.receipt.event_id}-${idx}`}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div className="badge">{evt.receipt.stream_type}</div>
                <small>{ts}</small>
              </div>
              <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
                <small>{evt.receipt.source}</small>
                {Object.entries(evt.metrics || {}).map(([k, v]) => (
                  <span key={k} className="metric-pill">
                    {k}: {typeof v === "number" ? v.toFixed(3) : String(v)}
                  </span>
                ))}
              </div>
            </div>
          );
          })}

          {recentEvents.slice(0, 10).map((evt, idx) => (
            <div className="event" key={`${evt.event.event_id}-recent-${idx}`}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div className="badge">{evt.event.stream_type}</div>
                <small>{formatTime(evt.received_at)}</small>
              </div>
              <div style={{ marginTop: 6 }}>
                <small>{evt.event.source}</small>
              </div>
            </div>
          ))}
          {liveStream.length === 0 && recentEvents.length === 0 && <div className="event">No events yet.</div>}
        </div>
      </aside>
    </div>
  );
}
