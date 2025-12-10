import Foundation
import H3LIXCore

enum MockData {
    static func demoSession() -> SessionSummary {
        SessionSummary(
            id: "demo-session",
            experimentID: "demo",
            subjectID: "P-00",
            status: "demo",
            startedUTC: ISO8601DateFormatter().string(from: Date()),
            endedUTC: nil
        )
    }

    static func demoSnapshot() -> SnapshotResponse {
        let somatic = SomaticStatePayload(
            tRelMs: 1000,
            windowMs: 200,
            features: ["hrv": 0.6, "eda": 0.4],
            innovation: nil,
            covarianceDiag: nil,
            globalUncertaintyScore: 0.3,
            changePoint: true,
            anomalyScore: 0.8,
            anticipatoryMarkers: []
        )
        let belief = SymbolicBelief(id: "b1", kind: "entity", label: "Demo belief", description: nil, valence: 0.2, intensity: 0.7, recency: 0.6, stability: 0.6, confidence: 0.8, importance: 0.7)
        let symbolic = SymbolicStatePayload(
            tRelMs: 1000,
            beliefRevisionID: "rev1",
            beliefs: [belief],
            predictions: [],
            uncertaintyRegions: []
        )
        let noetic = NoeticStatePayload(
            tRelMs: 1000,
            windowMs: 200,
            globalCoherenceScore: 0.7,
            entropyChange: 0.1,
            streamCorrelations: [],
            coherenceSpectrum: [NoeticSpectrumBand(bandLabel: "alpha", freqRangeHz: [8, 12], coherenceStrength: 0.7)],
            intuitiveAccuracyEstimate: NoeticIntuitiveAccuracyEstimate(pBetterThanBaseline: 0.6, calibrationError: nil)
        )

        let node = MpgNode(
            id: "n1",
            label: "Demo Node",
            description: "Sample",
            layerTags: ["demo"],
            metrics: .init(valence: 0.1, intensity: 0.8, recency: 0.3, stability: 0.7),
            confidence: 0.8,
            importance: 0.8,
            roles: ["hub"],
            evidencePreview: [],
            reasoningProvenance: nil
        )
        let edge = MpgEdge(id: "e1", source: "n1", target: "n1", type: "self", strength: 0.5, confidence: 0.8)
        let segment = MpgSegment(
            id: "seg1",
            label: "Segment 1",
            level: 0,
            memberNodeIds: ["n1"],
            cohesion: 0.6,
            averageImportance: 0.8,
            averageConfidence: 0.8,
            affectiveLoad: 0.2
        )
        let mpg = SnapshotMpg(
            mpgID: "mpg-demo",
            levelSummaries: [MpgLevelSummary(level: 0, nodeCount: 1, segmentCount: 1)],
            baseSubgraph: MpgSubgraphResponse(mpgID: "mpg-demo", level: 0, centerNodeID: nil, nodes: [node], edges: [edge], segments: [segment])
        )

        return SnapshotResponse(
            sessionID: "demo-session",
            tRelMs: 1000,
            somatic: somatic,
            symbolic: symbolic,
            noetic: noetic,
            lastDecisionCycle: nil,
            mpg: mpg
        )
    }
}
