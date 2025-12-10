import { create } from "zustand";
import {
  MpgDeltaPayload,
  NoeticStatePayload,
  SnapshotResponse,
  SomaticStatePayload,
  SymbolicStatePayload,
  TelemetryEnvelope,
} from "./types";

type AnyEnvelope =
  | TelemetryEnvelope<SomaticStatePayload>
  | TelemetryEnvelope<SymbolicStatePayload>
  | TelemetryEnvelope<NoeticStatePayload>
  | TelemetryEnvelope<MpgDeltaPayload>;

type H3lixState = {
  snapshot?: SnapshotResponse;
  somatic?: SomaticStatePayload;
  symbolic?: SymbolicStatePayload;
  noetic?: NoeticStatePayload;
  mpgDeltas: MpgDeltaPayload[];
  setSnapshot: (snap: SnapshotResponse) => void;
  applyEnvelope: (env: AnyEnvelope) => void;
};

export const useH3lixStore = create<H3lixState>((set) => ({
  snapshot: undefined,
  somatic: undefined,
  symbolic: undefined,
  noetic: undefined,
  mpgDeltas: [],
  setSnapshot: (snap) =>
    set({
      snapshot: snap,
      somatic: snap.somatic,
      symbolic: snap.symbolic,
      noetic: snap.noetic,
    }),
  applyEnvelope: (env) =>
    set((state) => {
      switch (env.message_type) {
        case "somatic_state":
          return { ...state, somatic: env.payload as SomaticStatePayload };
        case "symbolic_state":
          return { ...state, symbolic: env.payload as SymbolicStatePayload };
        case "noetic_state":
          return { ...state, noetic: env.payload as NoeticStatePayload };
        case "mpg_delta":
          return { ...state, mpgDeltas: [...state.mpgDeltas, env.payload as MpgDeltaPayload] };
        default:
          return state;
      }
    }),
}));
