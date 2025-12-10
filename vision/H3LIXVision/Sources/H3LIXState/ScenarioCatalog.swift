import Foundation
import H3LIXCore

public struct ScenarioPreset: Identifiable, Hashable {
    public let id: String
    public let title: String
    public let subtitle: String
    public let snapshot: SnapshotResponse
    public let rogue: RogueVariableEventPayload?
    public let mufs: MufsEventPayload?

    public init(
        id: String,
        title: String,
        subtitle: String,
        snapshot: SnapshotResponse,
        rogue: RogueVariableEventPayload? = nil,
        mufs: MufsEventPayload? = nil
    ) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.snapshot = snapshot
        self.rogue = rogue
        self.mufs = mufs
    }
}

@MainActor
public enum ScenarioCatalog {
    public static let presets: [ScenarioPreset] = [
        ScenarioPreset(
            id: "baseline",
            title: "Baseline",
            subtitle: "Calm body, balanced coherence.",
            snapshot: snapshot(
                sessionID: "demo-baseline",
                tRelMs: 1200,
                somaticLevel: 0.35,
                changePoint: false,
                noeticCoherence: 0.55,
                entropyChange: 0.06,
                nodeLabel: "Steady plan",
                nodeImportance: 0.45,
                segmentID: "seg-baseline"
            )
        ),
        ScenarioPreset(
            id: "rogue-surge",
            title: "Rogue surge",
            subtitle: "Somatic spike with rogue highlight.",
            snapshot: snapshot(
                sessionID: "demo-rogue",
                tRelMs: 2600,
                somaticLevel: 0.82,
                changePoint: true,
                noeticCoherence: 0.42,
                entropyChange: 0.18,
                nodeLabel: "Rogue signal",
                nodeImportance: 0.82,
                segmentID: "seg-rogue"
            ),
            rogue: rogueEvent(mpgID: "mpg-demo-rogue", segmentID: "seg-rogue", hubNodeID: "n-demo-rogue-hub")
        ),
        ScenarioPreset(
            id: "mufs-detour",
            title: "MUFS detour",
            subtitle: "Decision in flux; MUFS callout.",
            snapshot: snapshot(
                sessionID: "demo-mufs",
                tRelMs: 3400,
                somaticLevel: 0.58,
                changePoint: false,
                noeticCoherence: 0.31,
                entropyChange: -0.22,
                nodeLabel: "Conflicting cues",
                nodeImportance: 0.67,
                segmentID: "seg-mufs"
            ),
            mufs: mufsEvent(mpgID: "mpg-demo-mufs", nodeIDs: ["n-demo-mufs-hub", "n-demo-mufs-context"])
        )
    ]

    private static func snapshot(
        sessionID: String,
        tRelMs: Int,
        somaticLevel: Double,
        changePoint: Bool,
        noeticCoherence: Double,
        entropyChange: Double,
        nodeLabel: String,
        nodeImportance: Double,
        segmentID: String
    ) -> SnapshotResponse {
        let somatic = SomaticStatePayload(
            tRelMs: tRelMs,
            windowMs: 300,
            features: [
                "hrv": somaticLevel,
                "eda": max(0.1, somaticLevel - 0.15),
                "respiration": 0.45 + somaticLevel * 0.3
            ],
            innovation: nil,
            covarianceDiag: nil,
            globalUncertaintyScore: max(0.1, somaticLevel - 0.2),
            changePoint: changePoint,
            anomalyScore: changePoint ? max(0.5, somaticLevel) : somaticLevel * 0.25,
            anticipatoryMarkers: []
        )

        let beliefs: [SymbolicBelief] = [
            SymbolicBelief(
                id: "\(sessionID)-hub",
                kind: "entity",
                label: nodeLabel,
                description: "Primary belief driving this scenario.",
                valence: 0.2,
                intensity: nodeImportance,
                recency: 0.7,
                stability: 0.5,
                confidence: 0.75,
                importance: nodeImportance
            ),
            SymbolicBelief(
                id: "\(sessionID)-context",
                kind: "context",
                label: "Context",
                description: "Background cues",
                valence: 0.1,
                intensity: 0.4,
                recency: 0.5,
                stability: 0.7,
                confidence: 0.6,
                importance: 0.5
            )
        ]

        let symbolic = SymbolicStatePayload(
            tRelMs: tRelMs,
            beliefRevisionID: "rev-\(sessionID)",
            beliefs: beliefs,
            predictions: [],
            uncertaintyRegions: []
        )

        let noetic = NoeticStatePayload(
            tRelMs: tRelMs,
            windowMs: 300,
            globalCoherenceScore: noeticCoherence,
            entropyChange: entropyChange,
            streamCorrelations: [
                decode(StreamCorrelationDTO(streamX: .somatic, streamY: .symbolic, r: noeticCoherence * 0.8)),
                decode(StreamCorrelationDTO(streamX: .symbolic, streamY: .behavioral, r: 0.25 + noeticCoherence * 0.3))
            ],
            coherenceSpectrum: [
                NoeticSpectrumBand(bandLabel: "alpha", freqRangeHz: [8, 12], coherenceStrength: max(0.1, noeticCoherence - 0.1)),
                NoeticSpectrumBand(bandLabel: "gamma", freqRangeHz: [35, 45], coherenceStrength: max(0.1, 0.4 - entropyChange))
            ],
            intuitiveAccuracyEstimate: NoeticIntuitiveAccuracyEstimate(pBetterThanBaseline: max(0.1, min(0.95, noeticCoherence + 0.15)))
        )

        let hubNode = MpgNode(
            id: "n-\(sessionID)-hub",
            label: nodeLabel,
            description: "Hub concept",
            layerTags: ["noetic"],
            metrics: .init(valence: 0.2, intensity: nodeImportance, recency: 0.6, stability: 0.6),
            confidence: 0.75,
            importance: nodeImportance,
            roles: ["hub"],
            evidencePreview: [],
            reasoningProvenance: nil
        )
        var nodes: [MpgNode] = [hubNode]
        var edges: [MpgEdge] = []

        let supportNode = MpgNode(
            id: "n-\(sessionID)-context",
            label: "Context cue",
            description: "Supporting observation",
            layerTags: ["symbolic"],
            metrics: .init(valence: 0.1, intensity: 0.4, recency: 0.5, stability: 0.7),
            confidence: 0.6,
            importance: 0.5,
            roles: ["support"],
            evidencePreview: [],
            reasoningProvenance: nil
        )
        nodes.append(supportNode)
        edges.append(MpgEdge(id: "e-\(sessionID)-support", source: hubNode.id, target: supportNode.id, type: "supports", strength: 0.6, confidence: 0.7))
        edges.append(MpgEdge(id: "e-\(sessionID)-back", source: supportNode.id, target: hubNode.id, type: "reinforces", strength: 0.4, confidence: 0.55))

        for i in 0..<6 {
            let id = "n-\(sessionID)-cue\(i)"
            let node = MpgNode(
                id: id,
                label: "Cue \(i + 1)",
                description: "Peripheral signal",
                layerTags: ["symbolic"],
                metrics: .init(valence: 0.05 * Double(i + 1), intensity: 0.3 + 0.05 * Double(i), recency: 0.4, stability: 0.6),
                confidence: 0.45 + 0.05 * Double(i),
                importance: 0.35 + 0.04 * Double(i),
                roles: ["cue"],
                evidencePreview: [],
                reasoningProvenance: nil
            )
            nodes.append(node)
            edges.append(MpgEdge(id: "e-\(sessionID)-hub-\(i)", source: hubNode.id, target: node.id, type: "influences", strength: 0.3 + 0.05 * Double(i), confidence: 0.5))
            edges.append(MpgEdge(id: "e-\(sessionID)-\(i)-hub", source: node.id, target: hubNode.id, type: "feeds", strength: 0.25, confidence: 0.45))
        }

        let avgImportance = nodes.map(\.importance).average
        let avgConfidence = nodes.map(\.confidence).average
        let segment = MpgSegment(
            id: segmentID,
            label: "Cluster A",
            level: 0,
            memberNodeIds: nodes.map(\.id),
            cohesion: min(1.0, 0.4 + nodeImportance * 0.5),
            averageImportance: avgImportance,
            averageConfidence: avgConfidence,
            affectiveLoad: changePoint ? 0.6 : 0.2
        )
        let mpg = SnapshotMpg(
            mpgID: "mpg-\(sessionID)",
            levelSummaries: [MpgLevelSummary(level: 0, nodeCount: nodes.count, segmentCount: 1)],
            baseSubgraph: MpgSubgraphResponse(
                mpgID: "mpg-\(sessionID)",
                level: 0,
                centerNodeID: hubNode.id,
                nodes: nodes,
                edges: edges,
                segments: [segment]
            )
        )

        return SnapshotResponse(
            sessionID: sessionID,
            tRelMs: tRelMs,
            somatic: somatic,
            symbolic: symbolic,
            noetic: noetic,
            lastDecisionCycle: nil,
            mpg: mpg
        )
    }

    private static func rogueEvent(mpgID: String, segmentID: String, hubNodeID: String) -> RogueVariableEventPayload {
        let shapley = RogueShapleyDTO(meanAbsContrib: 0.22, stdAbsContrib: 0.08, candidateAbsContrib: 0.48, zScore: 2.1)
        let impact = RogueImpactDTO(rateOfChange: 0.78, breadthOfImpact: 0.62, amplification: 0.91, emotionalLoad: 0.4)
        let dto = RogueEventDTO(
            rogueID: "rv-\(segmentID)",
            mpgID: mpgID,
            candidateType: "segment",
            levelRange: [0, 1],
            segmentIDs: [segmentID],
            pathwayNodes: [hubNodeID],
            shapleyStats: shapley,
            potencyIndex: 0.86,
            impactFactors: impact
        )
        return decode(dto)
    }

    private static func mufsEvent(mpgID: String, nodeIDs: [String]) -> MufsEventPayload {
        let full = DecisionUtilityDTO(choice: "approach", utility: ["approach": 0.62, "avoid": 0.38])
        let without = DecisionUtilityDTO(choice: "avoid", utility: ["approach": 0.41, "avoid": 0.59])
        let dto = MufsEventDTO(
            mufsID: "mufs-\(mpgID)",
            decisionID: "dec-\(mpgID)",
            mpgID: mpgID,
            unawarenessTypes: [.iu, .pu],
            inputUnawareRefs: ["stimulus-a", "stimulus-b"],
            processUnawareNodeIds: nodeIDs,
            decisionFull: full,
            decisionWithoutU: without,
            minimal: false,
            searchMetadata: [:]
        )
        return decode(dto)
    }
}

// MARK: - Helper DTOs / builders

private struct StreamCorrelationDTO: Codable {
    let streamX: StreamName
    let streamY: StreamName
    let r: Double

    enum CodingKeys: String, CodingKey {
        case streamX = "stream_x"
        case streamY = "stream_y"
        case r
    }
}

private struct RogueImpactDTO: Codable {
    let rateOfChange: Double
    let breadthOfImpact: Double
    let amplification: Double
    let emotionalLoad: Double

    enum CodingKeys: String, CodingKey {
        case rateOfChange = "rate_of_change"
        case breadthOfImpact = "breadth_of_impact"
        case amplification
        case emotionalLoad = "emotional_load"
    }
}

private struct RogueShapleyDTO: Codable {
    let meanAbsContrib: Double
    let stdAbsContrib: Double
    let candidateAbsContrib: Double
    let zScore: Double

    enum CodingKeys: String, CodingKey {
        case meanAbsContrib = "mean_abs_contrib"
        case stdAbsContrib = "std_abs_contrib"
        case candidateAbsContrib = "candidate_abs_contrib"
        case zScore = "z_score"
    }
}

private struct RogueEventDTO: Codable {
    let rogueID: String
    let mpgID: String
    let candidateType: String
    let levelRange: [Int]
    let segmentIDs: [String]?
    let pathwayNodes: [String]?
    let shapleyStats: RogueShapleyDTO
    let potencyIndex: Double
    let impactFactors: RogueImpactDTO

    enum CodingKeys: String, CodingKey {
        case rogueID = "rogue_id"
        case mpgID = "mpg_id"
        case candidateType = "candidate_type"
        case levelRange = "level_range"
        case segmentIDs = "segment_ids"
        case pathwayNodes = "pathway_nodes"
        case shapleyStats = "shapley_stats"
        case potencyIndex = "potency_index"
        case impactFactors = "impact_factors"
    }
}

private struct DecisionUtilityDTO: Codable {
    let choice: String
    let utility: [String: Double]
}

private struct MufsEventDTO: Codable {
    let mufsID: String
    let decisionID: String
    let mpgID: String
    let unawarenessTypes: [UnawarenessType]
    let inputUnawareRefs: [String]?
    let processUnawareNodeIds: [String]?
    let decisionFull: DecisionUtilityDTO
    let decisionWithoutU: DecisionUtilityDTO
    let minimal: Bool
    let searchMetadata: [String: JSONValue]

    enum CodingKeys: String, CodingKey {
        case mufsID = "mufs_id"
        case decisionID = "decision_id"
        case mpgID = "mpg_id"
        case unawarenessTypes = "unawareness_types"
        case inputUnawareRefs = "input_unaware_refs"
        case processUnawareNodeIds = "process_unaware_node_ids"
        case decisionFull = "decision_full"
        case decisionWithoutU = "decision_without_U"
        case minimal
        case searchMetadata = "search_metadata"
    }
}

private func decode<T: Decodable, U: Encodable>(_ dto: U, as type: T.Type = T.self) -> T {
    let encoder = JSONEncoder()
    let decoder = JSONDecoder()
    guard let data = try? encoder.encode(dto), let decoded = try? decoder.decode(T.self, from: data) else {
        fatalError("Failed to build \(T.self) from DTO")
    }
    return decoded
}
