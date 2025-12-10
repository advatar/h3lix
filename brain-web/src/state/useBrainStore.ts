import { create } from "zustand";
import { BrainSnapshot, StreamUpdate, VisualEdge, VisualNode, QRVEvent } from "../types";

type BrainState = {
  nodes: VisualNode[];
  edges: VisualEdge[];
  recentEvents: BrainSnapshot["recent_events"];
  liveStream: StreamUpdate[];
  qrvEvents: QRVEvent[];
  connected: boolean;
  connecting: boolean;
  selectedNodeId: string | null;
  setSnapshot: (snapshot: BrainSnapshot) => void;
  pushStreamUpdate: (update: StreamUpdate) => void;
  addQRVEvent: (evt: QRVEvent) => void;
  setConnected: (connected: boolean) => void;
  setConnecting: (connecting: boolean) => void;
  setSelectedNode: (nodeId: string | null) => void;
  clearLive: () => void;
};

export const useBrainStore = create<BrainState>((set) => ({
  nodes: [],
  edges: [],
  recentEvents: [],
  liveStream: [],
  qrvEvents: [],
  connected: false,
  connecting: false,
  selectedNodeId: null,
  setSnapshot: (snapshot) =>
    set({
      nodes: snapshot.graph.nodes,
      edges: snapshot.graph.edges,
      recentEvents: snapshot.recent_events,
    }),
  pushStreamUpdate: (update) =>
    set((state) => ({
      liveStream: [update, ...state.liveStream].slice(0, 80),
    })),
  addQRVEvent: (evt) =>
    set((state) => ({
      qrvEvents: [evt, ...state.qrvEvents].slice(0, 50),
    })),
  setConnected: (connected) => set({ connected }),
  setConnecting: (connecting) => set({ connecting }),
  setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId }),
  clearLive: () => set({ liveStream: [], qrvEvents: [] }),
}));
