import Foundation

public enum MessageType: String, Codable, CaseIterable {
    case somaticState = "somatic_state"
    case symbolicState = "symbolic_state"
    case noeticState = "noetic_state"
    case decisionCycle = "decision_cycle"
    case mpgDelta = "mpg_delta"
    case rogueVariableEvent = "rogue_variable_event"
    case mufsEvent = "mufs_event"
}

public enum SourceLayer: String, Codable {
    case somatic = "Somatic"
    case symbolic = "Symbolic"
    case noetic = "Noetic"
    case mirrorCore = "MirrorCore"
    case mpg = "MPG"
}
extension SourceLayer: Sendable {}

public enum StreamName: String, Codable {
    case somatic
    case symbolic
    case behavioral
    case external
}
extension StreamName: Sendable {}

public enum StreamType: String, Codable {
    case somatic
    case text
    case audio
    case video
    case task
    case meta
}
extension StreamType: Sendable {}

public enum UnawarenessType: String, Codable {
    case iu = "IU"
    case pu = "PU"
}

public struct TelemetryEnvelope<Payload: Codable>: Codable, Identifiable {
    public var id: String { "\(messageType.rawValue)-\(sequence)" }

    public let version: String
    public let messageType: MessageType
    public let timestampUTC: String
    public let experimentID: String
    public let sessionID: String
    public let subjectID: String
    public let runID: String?
    public let sorkCycleID: String?
    public let decisionID: String?
    public let sourceLayer: SourceLayer
    public let sequence: Int
    public let payload: Payload

    public init(
        version: String = "1",
        messageType: MessageType,
        timestampUTC: String,
        experimentID: String,
        sessionID: String,
        subjectID: String,
        runID: String? = nil,
        sorkCycleID: String? = nil,
        decisionID: String? = nil,
        sourceLayer: SourceLayer,
        sequence: Int,
        payload: Payload
    ) {
        self.version = version
        self.messageType = messageType
        self.timestampUTC = timestampUTC
        self.experimentID = experimentID
        self.sessionID = sessionID
        self.subjectID = subjectID
        self.runID = runID
        self.sorkCycleID = sorkCycleID
        self.decisionID = decisionID
        self.sourceLayer = sourceLayer
        self.sequence = sequence
        self.payload = payload
    }

    enum CodingKeys: String, CodingKey {
        case version = "v"
        case messageType = "message_type"
        case timestampUTC = "timestamp_utc"
        case experimentID = "experiment_id"
        case sessionID = "session_id"
        case subjectID = "subject_id"
        case runID = "run_id"
        case sorkCycleID = "sork_cycle_id"
        case decisionID = "decision_id"
        case sourceLayer = "source_layer"
        case sequence
        case payload
    }
}

// MARK: - Telemetry payloads

public struct SomaticAnticipatoryMarker: Codable, Hashable {
    public let markerType: String
    public let leadTimeMs: Int
    public let confidence: Double

    enum CodingKeys: String, CodingKey {
        case markerType = "marker_type"
        case leadTimeMs = "lead_time_ms"
        case confidence
    }
}

public struct SomaticStatePayload: Codable, Hashable  {
    public let tRelMs: Int
    public let windowMs: Int
    public let features: [String: Double]
    public let innovation: [String: Double]?
    public let covarianceDiag: [String: Double]?
    public let globalUncertaintyScore: Double?
    public let changePoint: Bool
    public let anomalyScore: Double?
    public let anticipatoryMarkers: [SomaticAnticipatoryMarker]

    public init(
        tRelMs: Int,
        windowMs: Int,
        features: [String: Double],
        innovation: [String: Double]? = nil,
        covarianceDiag: [String: Double]? = nil,
        globalUncertaintyScore: Double? = nil,
        changePoint: Bool,
        anomalyScore: Double? = nil,
        anticipatoryMarkers: [SomaticAnticipatoryMarker]
    ) {
        self.tRelMs = tRelMs
        self.windowMs = windowMs
        self.features = features
        self.innovation = innovation
        self.covarianceDiag = covarianceDiag
        self.globalUncertaintyScore = globalUncertaintyScore
        self.changePoint = changePoint
        self.anomalyScore = anomalyScore
        self.anticipatoryMarkers = anticipatoryMarkers
    }

    enum CodingKeys: String, CodingKey {
        case tRelMs = "t_rel_ms"
        case windowMs = "window_ms"
        case features
        case innovation
        case covarianceDiag = "covariance_diag"
        case globalUncertaintyScore = "global_uncertainty_score"
        case changePoint = "change_point"
        case anomalyScore = "anomaly_score"
        case anticipatoryMarkers = "anticipatory_markers"
    }
}

public struct SymbolicBelief: Codable, Hashable, Identifiable {
    public let id: String
    public let kind: String
    public let label: String
    public let description: String?
    public let valence: Double?
    public let intensity: Double?
    public let recency: Double?
    public let stability: Double?
    public let confidence: Double
    public let importance: Double

    public init(
        id: String,
        kind: String,
        label: String,
        description: String? = nil,
        valence: Double? = nil,
        intensity: Double? = nil,
        recency: Double? = nil,
        stability: Double? = nil,
        confidence: Double,
        importance: Double
    ) {
        self.id = id
        self.kind = kind
        self.label = label
        self.description = description
        self.valence = valence
        self.intensity = intensity
        self.recency = recency
        self.stability = stability
        self.confidence = confidence
        self.importance = importance
    }
}

public struct SymbolicPredictionOption: Codable, Hashable {
    public let value: String
    public let probability: Double
}

public struct SymbolicPrediction: Codable, Hashable, Identifiable {
    public let id: String
    public let targetType: String
    public let horizonMs: Int?
    public let topk: [SymbolicPredictionOption]
    public let brierScore: Double?
    public let realizedValue: String?
    public let realizedError: Double?

    enum CodingKeys: String, CodingKey {
        case id
        case targetType = "target_type"
        case horizonMs = "horizon_ms"
        case topk
        case brierScore = "brier_score"
        case realizedValue = "realized_value"
        case realizedError = "realized_error"
    }
}

public struct SymbolicUncertaintyRegion: Codable, Hashable, Identifiable {
    public let id = UUID()
    public let label: String
    public let beliefIds: [String]
    public let comment: String?

    enum CodingKeys: String, CodingKey {
        case label
        case beliefIds = "belief_ids"
        case comment
    }
}

public struct SymbolicStatePayload: Codable, Hashable {
    public let tRelMs: Int
    public let beliefRevisionID: String
    public let beliefs: [SymbolicBelief]
    public let predictions: [SymbolicPrediction]
    public let uncertaintyRegions: [SymbolicUncertaintyRegion]

    public init(
        tRelMs: Int,
        beliefRevisionID: String,
        beliefs: [SymbolicBelief],
        predictions: [SymbolicPrediction] = [],
        uncertaintyRegions: [SymbolicUncertaintyRegion] = []
    ) {
        self.tRelMs = tRelMs
        self.beliefRevisionID = beliefRevisionID
        self.beliefs = beliefs
        self.predictions = predictions
        self.uncertaintyRegions = uncertaintyRegions
    }

    enum CodingKeys: String, CodingKey {
        case tRelMs = "t_rel_ms"
        case beliefRevisionID = "belief_revision_id"
        case beliefs
        case predictions
        case uncertaintyRegions = "uncertainty_regions"
    }
}

public struct NoeticStreamCorrelation: Codable, Hashable {
    public let streamX: StreamName
    public let streamY: StreamName
    public let r: Double

    enum CodingKeys: String, CodingKey {
        case streamX = "stream_x"
        case streamY = "stream_y"
        case r
    }
}

public struct NoeticSpectrumBand: Codable, Hashable {
    public let bandLabel: String
    public let freqRangeHz: [Double]
    public let coherenceStrength: Double

    public init(bandLabel: String, freqRangeHz: [Double], coherenceStrength: Double) {
        self.bandLabel = bandLabel
        self.freqRangeHz = freqRangeHz
        self.coherenceStrength = coherenceStrength
    }

    enum CodingKeys: String, CodingKey {
        case bandLabel = "band_label"
        case freqRangeHz = "freq_range_hz"
        case coherenceStrength = "coherence_strength"
    }
}

public struct NoeticIntuitiveAccuracyEstimate: Codable, Hashable {
    public let pBetterThanBaseline: Double
    public let calibrationError: Double?

    public init(pBetterThanBaseline: Double, calibrationError: Double? = nil) {
        self.pBetterThanBaseline = pBetterThanBaseline
        self.calibrationError = calibrationError
    }

    enum CodingKeys: String, CodingKey {
        case pBetterThanBaseline = "p_better_than_baseline"
        case calibrationError = "calibration_error"
    }
}

public struct NoeticStatePayload: Codable, Hashable {
    public let tRelMs: Int
    public let windowMs: Int
    public let globalCoherenceScore: Double
    public let entropyChange: Double
    public let streamCorrelations: [NoeticStreamCorrelation]
    public let coherenceSpectrum: [NoeticSpectrumBand]
    public let intuitiveAccuracyEstimate: NoeticIntuitiveAccuracyEstimate?

    public init(
        tRelMs: Int,
        windowMs: Int,
        globalCoherenceScore: Double,
        entropyChange: Double,
        streamCorrelations: [NoeticStreamCorrelation],
        coherenceSpectrum: [NoeticSpectrumBand],
        intuitiveAccuracyEstimate: NoeticIntuitiveAccuracyEstimate? = nil
    ) {
        self.tRelMs = tRelMs
        self.windowMs = windowMs
        self.globalCoherenceScore = globalCoherenceScore
        self.entropyChange = entropyChange
        self.streamCorrelations = streamCorrelations
        self.coherenceSpectrum = coherenceSpectrum
        self.intuitiveAccuracyEstimate = intuitiveAccuracyEstimate
    }

    enum CodingKeys: String, CodingKey {
        case tRelMs = "t_rel_ms"
        case windowMs = "window_ms"
        case globalCoherenceScore = "global_coherence_score"
        case entropyChange = "entropy_change"
        case streamCorrelations = "stream_correlations"
        case coherenceSpectrum = "coherence_spectrum"
        case intuitiveAccuracyEstimate = "intuitive_accuracy_estimate"
    }
}

public struct DecisionAction: Codable, Hashable {
    public let actionID: String
    public let label: String
    public let params: [String: JSONValue]?

    enum CodingKeys: String, CodingKey {
        case actionID = "action_id"
        case label
        case params
    }
}

public struct DecisionOutcome: Codable, Hashable {
    public let label: String
    public let metrics: [String: Double]
}

public struct NoeticAdjustment: Codable, Hashable {
    public let attentionGain: Double?
    public let decisionThresholdDelta: Double?
    public let learningRateDelta: Double?

    enum CodingKeys: String, CodingKey {
        case attentionGain = "attention_gain"
        case decisionThresholdDelta = "decision_threshold_delta"
        case learningRateDelta = "learning_rate_delta"
    }
}

public struct DecisionCyclePayload: Codable, Hashable {
    public let sorkCycleID: String
    public let decisionID: String?
    public let phase: String
    public let phaseStartedUTC: String
    public let phaseEndedUTC: String?
    public let stimulusRefs: [StimulusRef]?
    public let organismBeliefIDs: [String]?
    public let responseAction: DecisionAction?
    public let consequenceOutcome: DecisionOutcome?
    public let noeticAdjustments: NoeticAdjustment?

    enum CodingKeys: String, CodingKey {
        case sorkCycleID = "sork_cycle_id"
        case decisionID = "decision_id"
        case phase
        case phaseStartedUTC = "phase_started_utc"
        case phaseEndedUTC = "phase_ended_utc"
        case stimulusRefs = "stimulus_refs"
        case organismBeliefIDs = "organism_belief_ids"
        case responseAction = "response_action"
        case consequenceOutcome = "consequence_outcome"
        case noeticAdjustments = "noetic_adjustments"
    }
}

public struct StimulusRef: Codable, Hashable {
    public let channel: String
    public let refID: String

    enum CodingKeys: String, CodingKey {
        case channel
        case refID = "ref_id"
    }
}

public struct MpgEvidencePreview: Codable, Hashable {
    public let evidenceID: String
    public let snippet: String
    public let sourceClass: String
    public let timestampUTC: String

    enum CodingKeys: String, CodingKey {
        case evidenceID = "evidence_id"
        case snippet
        case sourceClass = "source_class"
        case timestampUTC = "timestamp_utc"
    }
}

public struct MpgNodeMetrics: Codable, Hashable {
    public let valence: Double
    public let intensity: Double
    public let recency: Double
    public let stability: Double

    public init(valence: Double, intensity: Double, recency: Double, stability: Double) {
        self.valence = valence
        self.intensity = intensity
        self.recency = recency
        self.stability = stability
    }
}

public struct MpgNode: Codable, Hashable, Identifiable {
    public let id: String
    public let label: String
    public let description: String?
    public let layerTags: [String]
    public let metrics: MpgNodeMetrics
    public let confidence: Double
    public let importance: Double
    public let roles: [String]
    public let evidencePreview: [MpgEvidencePreview]
    public let reasoningProvenance: String?

    public init(
        id: String,
        label: String,
        description: String?,
        layerTags: [String],
        metrics: MpgNodeMetrics,
        confidence: Double,
        importance: Double,
        roles: [String],
        evidencePreview: [MpgEvidencePreview],
        reasoningProvenance: String?
    ) {
        self.id = id
        self.label = label
        self.description = description
        self.layerTags = layerTags
        self.metrics = metrics
        self.confidence = confidence
        self.importance = importance
        self.roles = roles
        self.evidencePreview = evidencePreview
        self.reasoningProvenance = reasoningProvenance
    }

    enum CodingKeys: String, CodingKey {
        case id
        case label
        case description
        case layerTags = "layer_tags"
        case metrics
        case confidence
        case importance
        case roles
        case evidencePreview = "evidence_preview"
        case reasoningProvenance = "reasoning_provenance"
    }
}

public struct MpgEdge: Codable, Hashable, Identifiable {
    public let id: String
    public let source: String
    public let target: String
    public let type: String
    public let strength: Double
    public let confidence: Double

    public init(id: String, source: String, target: String, type: String, strength: Double, confidence: Double) {
        self.id = id
        self.source = source
        self.target = target
        self.type = type
        self.strength = strength
        self.confidence = confidence
    }
}

public struct MpgSegment: Codable, Hashable, Identifiable {
    public let id: String
    public let label: String
    public let level: Int
    public let memberNodeIds: [String]
    public let cohesion: Double
    public let averageImportance: Double
    public let averageConfidence: Double
    public let affectiveLoad: Double?

    public init(
        id: String,
        label: String,
        level: Int,
        memberNodeIds: [String],
        cohesion: Double,
        averageImportance: Double,
        averageConfidence: Double,
        affectiveLoad: Double? = nil
    ) {
        self.id = id
        self.label = label
        self.level = level
        self.memberNodeIds = memberNodeIds
        self.cohesion = cohesion
        self.averageImportance = averageImportance
        self.averageConfidence = averageConfidence
        self.affectiveLoad = affectiveLoad
    }

    enum CodingKeys: String, CodingKey {
        case id
        case label
        case level
        case memberNodeIds = "member_node_ids"
        case cohesion
        case averageImportance = "average_importance"
        case averageConfidence = "average_confidence"
        case affectiveLoad = "affective_load"
    }
}

public enum MpgOperationKind: String, Codable {
    case addNode = "add_node"
    case updateNode = "update_node"
    case addEdge = "add_edge"
    case updateEdge = "update_edge"
    case addSegment = "add_segment"
    case updateSegment = "update_segment"
}
extension MpgOperationKind: Sendable {}

public struct MpgOperation: Codable, Hashable {
    public let kind: MpgOperationKind
    public let node: MpgNode?
    public let nodeID: String?
    public let edge: MpgEdge?
    public let edgeID: String?
    public let segment: MpgSegment?
    public let segmentID: String?
    public let patch: [String: JSONValue]?

    enum CodingKeys: String, CodingKey {
        case kind
        case node
        case nodeID = "node_id"
        case edge
        case edgeID = "edge_id"
        case segment
        case segmentID = "segment_id"
        case patch
    }
}

public struct MpgDeltaPayload: Codable, Hashable  {
    public let mpgID: String
    public let level: Int
    public let deltaID: String
    public let operations: [MpgOperation]

    enum CodingKeys: String, CodingKey {
        case mpgID = "mpg_id"
        case level
        case deltaID = "delta_id"
        case operations
    }
}

public struct RogueVariableImpactFactors: Codable, Hashable {
    public let rateOfChange: Double
    public let breadthOfImpact: Double
    public let amplification: Double
    public let emotionalLoad: Double

    enum CodingKeys: String, CodingKey {
        case rateOfChange = "rate_of_change"
        case breadthOfImpact = "breadth_of_impact"
        case amplification
        case emotionalLoad = "emotional_load"
    }
}

public struct RogueVariableShapleyStats: Codable, Hashable {
    public let meanAbsContrib: Double
    public let stdAbsContrib: Double
    public let candidateAbsContrib: Double
    public let zScore: Double

    enum CodingKeys: String, CodingKey {
        case meanAbsContrib = "mean_abs_contrib"
        case stdAbsContrib = "std_abs_contrib"
        case candidateAbsContrib = "candidate_abs_contrib"
        case zScore = "z_score"
    }
}

public struct RogueVariableEventPayload: Codable, Hashable {
    public let rogueID: String
    public let mpgID: String
    public let candidateType: String
    public let levelRange: [Int]
    public let segmentIDs: [String]?
    public let pathwayNodes: [String]?
    public let shapleyStats: RogueVariableShapleyStats
    public let potencyIndex: Double
    public let impactFactors: RogueVariableImpactFactors

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

public struct DecisionUtility: Codable, Hashable {
    public let choice: String
    public let utility: [String: Double]
}

public struct MufsEventPayload: Codable, Hashable {
    public let mufsID: String
    public let decisionID: String
    public let mpgID: String
    public let unawarenessTypes: [UnawarenessType]
    public let inputUnawareRefs: [String]?
    public let processUnawareNodeIds: [String]?
    public let decisionFull: DecisionUtility
    public let decisionWithoutU: DecisionUtility
    public let minimal: Bool
    public let searchMetadata: [String: JSONValue]?

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

// MARK: - Snapshot / session models

public struct SessionSummary: Codable, Hashable, Identifiable {
    public let id: String
    public let experimentID: String
    public let subjectID: String
    public let status: String
    public let startedUTC: String
    public let endedUTC: String?

    public init(id: String, experimentID: String, subjectID: String, status: String, startedUTC: String, endedUTC: String? = nil) {
        self.id = id
        self.experimentID = experimentID
        self.subjectID = subjectID
        self.status = status
        self.startedUTC = startedUTC
        self.endedUTC = endedUTC
    }

    enum CodingKeys: String, CodingKey {
        case id = "session_id"
        case experimentID = "experiment_id"
        case subjectID = "subject_id"
        case status
        case startedUTC = "started_utc"
        case endedUTC = "ended_utc"
    }
}

public struct MpgLevelSummary: Codable, Hashable {
    public let level: Int
    public let nodeCount: Int
    public let segmentCount: Int

    public init(level: Int, nodeCount: Int, segmentCount: Int) {
        self.level = level
        self.nodeCount = nodeCount
        self.segmentCount = segmentCount
    }

    enum CodingKeys: String, CodingKey {
        case level
        case nodeCount = "node_count"
        case segmentCount = "segment_count"
    }
}

public struct MpgSubgraphResponse: Codable, Hashable {
    public let mpgID: String
    public let level: Int
    public let centerNodeID: String?
    public let nodes: [MpgNode]
    public let edges: [MpgEdge]
    public let segments: [MpgSegment]

    public init(
        mpgID: String,
        level: Int,
        centerNodeID: String? = nil,
        nodes: [MpgNode],
        edges: [MpgEdge],
        segments: [MpgSegment]
    ) {
        self.mpgID = mpgID
        self.level = level
        self.centerNodeID = centerNodeID
        self.nodes = nodes
        self.edges = edges
        self.segments = segments
    }

    enum CodingKeys: String, CodingKey {
        case mpgID = "mpg_id"
        case level
        case centerNodeID = "center_node_id"
        case nodes
        case edges
        case segments
    }
}

public struct SnapshotMpg: Codable, Hashable {
    public let mpgID: String
    public let levelSummaries: [MpgLevelSummary]
    public let baseSubgraph: MpgSubgraphResponse

    public init(mpgID: String, levelSummaries: [MpgLevelSummary], baseSubgraph: MpgSubgraphResponse) {
        self.mpgID = mpgID
        self.levelSummaries = levelSummaries
        self.baseSubgraph = baseSubgraph
    }

    enum CodingKeys: String, CodingKey {
        case mpgID = "mpg_id"
        case levelSummaries = "level_summaries"
        case baseSubgraph = "base_subgraph"
    }
}

public struct SnapshotResponse: Codable, Hashable {
    public let sessionID: String
    public let tRelMs: Int
    public let somatic: SomaticStatePayload
    public let symbolic: SymbolicStatePayload
    public let noetic: NoeticStatePayload
    public let lastDecisionCycle: DecisionCyclePayload?
    public let mpg: SnapshotMpg

    public init(
        sessionID: String,
        tRelMs: Int,
        somatic: SomaticStatePayload,
        symbolic: SymbolicStatePayload,
        noetic: NoeticStatePayload,
        lastDecisionCycle: DecisionCyclePayload? = nil,
        mpg: SnapshotMpg
    ) {
        self.sessionID = sessionID
        self.tRelMs = tRelMs
        self.somatic = somatic
        self.symbolic = symbolic
        self.noetic = noetic
        self.lastDecisionCycle = lastDecisionCycle
        self.mpg = mpg
    }

    enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case tRelMs = "t_rel_ms"
        case somatic
        case symbolic
        case noetic
        case lastDecisionCycle = "last_decision_cycle"
        case mpg
    }
}

public struct ReplayResponse: Codable, Hashable {
    public let sessionID: String
    public let fromMs: Int
    public let toMs: Int
    public let messages: [AnyTelemetryEnvelope]

    enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case fromMs = "from_ms"
        case toMs = "to_ms"
        case messages
    }
}

public struct DecisionTraceResponse: Codable, Hashable {
    public let sessionID: String
    public let decisionID: String
    public let phases: [DecisionCyclePayload]
    public let mufsEvents: [MufsEventPayload]
    public let rogueVariableEvents: [RogueVariableEventPayload]
    public let mpgFull: MpgSubgraphResponse?
    public let mpgWithoutMufs: MpgSubgraphResponse?

    enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case decisionID = "decision_id"
        case phases
        case mufsEvents = "mufs_events"
        case rogueVariableEvents = "rogue_variable_events"
        case mpgFull = "mpg_full"
        case mpgWithoutMufs = "mpg_without_mufs"
    }
}

// MARK: - Generic JSON helper

public enum JSONValue: Codable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case array([JSONValue])
    case object([String: JSONValue])
    case null

    public init(from decoder: Decoder) throws {
        if let keyed = try? decoder.container(keyedBy: DynamicCodingKey.self) {
            var values: [String: JSONValue] = [:]
            for key in keyed.allKeys {
                values[key.stringValue] = try keyed.decode(JSONValue.self, forKey: key)
            }
            self = .object(values)
            return
        }

        if var unkeyed = try? decoder.unkeyedContainer() {
            var items: [JSONValue] = []
            while !unkeyed.isAtEnd {
                let value = try unkeyed.decode(JSONValue.self)
                items.append(value)
            }
            self = .array(items)
            return
        }

        let single = try decoder.singleValueContainer()
        if single.decodeNil() {
            self = .null
        } else if let b = try? single.decode(Bool.self) {
            self = .bool(b)
        } else if let n = try? single.decode(Double.self) {
            self = .number(n)
        } else if let s = try? single.decode(String.self) {
            self = .string(s)
        } else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "Unsupported JSON value"))
        }
    }

    public func encode(to encoder: Encoder) throws {
        switch self {
        case .string(let value):
            var container = encoder.singleValueContainer()
            try container.encode(value)
        case .number(let value):
            var container = encoder.singleValueContainer()
            try container.encode(value)
        case .bool(let value):
            var container = encoder.singleValueContainer()
            try container.encode(value)
        case .array(let values):
            var container = encoder.unkeyedContainer()
            try values.forEach { try container.encode($0) }
        case .object(let dict):
            var container = encoder.container(keyedBy: DynamicCodingKey.self)
            for (key, value) in dict {
                try container.encode(value, forKey: DynamicCodingKey(stringValue: key))
            }
        case .null:
            var container = encoder.singleValueContainer()
            try container.encodeNil()
        }
    }

    private struct DynamicCodingKey: CodingKey {
        var stringValue: String
        var intValue: Int?

        init(stringValue: String) {
            self.stringValue = stringValue
            self.intValue = nil
        }

        init?(intValue: Int) {
            self.stringValue = "\(intValue)"
            self.intValue = intValue
        }
    }
}

extension JSONValue: Equatable {
    public static func == (lhs: JSONValue, rhs: JSONValue) -> Bool {
        switch (lhs, rhs) {
        case (.string(let l), .string(let r)): return l == r
        case (.number(let l), .number(let r)): return l == r
        case (.bool(let l), .bool(let r)): return l == r
        case (.array(let l), .array(let r)): return l == r
        case (.object(let l), .object(let r)): return l == r
        case (.null, .null): return true
        default: return false
        }
    }
}

extension JSONValue: Hashable {
    public func hash(into hasher: inout Hasher) {
        switch self {
        case .string(let value):
            hasher.combine(0)
            hasher.combine(value)
        case .number(let value):
            hasher.combine(1)
            hasher.combine(value)
        case .bool(let value):
            hasher.combine(2)
            hasher.combine(value)
        case .array(let values):
            hasher.combine(3)
            values.forEach { hasher.combine($0) }
        case .object(let dict):
            hasher.combine(4)
            dict.keys.sorted().forEach { key in
                hasher.combine(key)
                hasher.combine(dict[key])
            }
        case .null:
            hasher.combine(5)
        }
    }
}

// MARK: - Type-erased envelope

public enum TelemetryPayload: Hashable, Sendable {
    case somatic(SomaticStatePayload)
    case symbolic(SymbolicStatePayload)
    case noetic(NoeticStatePayload)
    case decision(DecisionCyclePayload)
    case mpgDelta(MpgDeltaPayload)
    case rogueVariable(RogueVariableEventPayload)
    case mufs(MufsEventPayload)
    case unknown(JSONValue)
}

public struct AnyTelemetryEnvelope: Codable, Identifiable, Hashable, Sendable {
    public var id: String { "\(messageType.rawValue)-\(sequence)" }

    public let version: String
    public let messageType: MessageType
    public let timestampUTC: String
    public let experimentID: String
    public let sessionID: String
    public let subjectID: String
    public let runID: String?
    public let sorkCycleID: String?
    public let decisionID: String?
    public let sourceLayer: SourceLayer
    public let sequence: Int
    public let payload: TelemetryPayload

    enum CodingKeys: String, CodingKey {
        case version = "v"
        case messageType = "message_type"
        case timestampUTC = "timestamp_utc"
        case experimentID = "experiment_id"
        case sessionID = "session_id"
        case subjectID = "subject_id"
        case runID = "run_id"
        case sorkCycleID = "sork_cycle_id"
        case decisionID = "decision_id"
        case sourceLayer = "source_layer"
        case sequence
        case payload
    }

    public init(
        version: String,
        messageType: MessageType,
        timestampUTC: String,
        experimentID: String,
        sessionID: String,
        subjectID: String,
        runID: String?,
        sorkCycleID: String?,
        decisionID: String?,
        sourceLayer: SourceLayer,
        sequence: Int,
        payload: TelemetryPayload
    ) {
        self.version = version
        self.messageType = messageType
        self.timestampUTC = timestampUTC
        self.experimentID = experimentID
        self.sessionID = sessionID
        self.subjectID = subjectID
        self.runID = runID
        self.sorkCycleID = sorkCycleID
        self.decisionID = decisionID
        self.sourceLayer = sourceLayer
        self.sequence = sequence
        self.payload = payload
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let version = try container.decode(String.self, forKey: .version)
        let messageType = try container.decode(MessageType.self, forKey: .messageType)
        let timestampUTC = try container.decode(String.self, forKey: .timestampUTC)
        let experimentID = try container.decode(String.self, forKey: .experimentID)
        let sessionID = try container.decode(String.self, forKey: .sessionID)
        let subjectID = try container.decode(String.self, forKey: .subjectID)
        let runID = try container.decodeIfPresent(String.self, forKey: .runID)
        let sorkCycleID = try container.decodeIfPresent(String.self, forKey: .sorkCycleID)
        let decisionID = try container.decodeIfPresent(String.self, forKey: .decisionID)
        let sourceLayer = try container.decode(SourceLayer.self, forKey: .sourceLayer)
        let sequence = try container.decode(Int.self, forKey: .sequence)

        let payload: TelemetryPayload
        switch messageType {
        case .somaticState:
            payload = .somatic(try container.decode(SomaticStatePayload.self, forKey: .payload))
        case .symbolicState:
            payload = .symbolic(try container.decode(SymbolicStatePayload.self, forKey: .payload))
        case .noeticState:
            payload = .noetic(try container.decode(NoeticStatePayload.self, forKey: .payload))
        case .decisionCycle:
            payload = .decision(try container.decode(DecisionCyclePayload.self, forKey: .payload))
        case .mpgDelta:
            payload = .mpgDelta(try container.decode(MpgDeltaPayload.self, forKey: .payload))
        case .rogueVariableEvent:
            payload = .rogueVariable(try container.decode(RogueVariableEventPayload.self, forKey: .payload))
        case .mufsEvent:
            payload = .mufs(try container.decode(MufsEventPayload.self, forKey: .payload))
        }

        self.init(
            version: version,
            messageType: messageType,
            timestampUTC: timestampUTC,
            experimentID: experimentID,
            sessionID: sessionID,
            subjectID: subjectID,
            runID: runID,
            sorkCycleID: sorkCycleID,
            decisionID: decisionID,
            sourceLayer: sourceLayer,
            sequence: sequence,
            payload: payload
        )
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(version, forKey: .version)
        try container.encode(messageType, forKey: .messageType)
        try container.encode(timestampUTC, forKey: .timestampUTC)
        try container.encode(experimentID, forKey: .experimentID)
        try container.encode(sessionID, forKey: .sessionID)
        try container.encode(subjectID, forKey: .subjectID)
        try container.encodeIfPresent(runID, forKey: .runID)
        try container.encodeIfPresent(sorkCycleID, forKey: .sorkCycleID)
        try container.encodeIfPresent(decisionID, forKey: .decisionID)
        try container.encode(sourceLayer, forKey: .sourceLayer)
        try container.encode(sequence, forKey: .sequence)

        switch payload {
        case .somatic(let value):
            try container.encode(value, forKey: .payload)
        case .symbolic(let value):
            try container.encode(value, forKey: .payload)
        case .noetic(let value):
            try container.encode(value, forKey: .payload)
        case .decision(let value):
            try container.encode(value, forKey: .payload)
        case .mpgDelta(let value):
            try container.encode(value, forKey: .payload)
        case .rogueVariable(let value):
            try container.encode(value, forKey: .payload)
        case .mufs(let value):
            try container.encode(value, forKey: .payload)
        case .unknown(let value):
            try container.encode(value, forKey: .payload)
        }
    }
}

// MARK: - Sendable conformances for concurrency

extension SomaticAnticipatoryMarker: Sendable {}
extension SomaticStatePayload: Sendable {}
extension SymbolicBelief: Sendable {}
extension SymbolicPredictionOption: Sendable {}
extension SymbolicPrediction: Sendable {}
extension SymbolicUncertaintyRegion: Sendable {}
extension SymbolicStatePayload: Sendable {}
extension NoeticStreamCorrelation: Sendable {}
extension NoeticSpectrumBand: Sendable {}
extension NoeticIntuitiveAccuracyEstimate: Sendable {}
extension NoeticStatePayload: Sendable {}
extension DecisionAction: Sendable {}
extension DecisionOutcome: Sendable {}
extension NoeticAdjustment: Sendable {}
extension StimulusRef: Sendable {}
extension DecisionCyclePayload: Sendable {}
extension MpgEvidencePreview: Sendable {}
extension MpgNodeMetrics: Sendable {}
extension MpgNode: Sendable {}
extension MpgEdge: Sendable {}
extension MpgSegment: Sendable {}
extension MpgOperation: Sendable {}
extension MpgDeltaPayload: Sendable {}
extension RogueVariableImpactFactors: Sendable {}
extension RogueVariableShapleyStats: Sendable {}
extension RogueVariableEventPayload: Sendable {}
extension UnawarenessType: Sendable {}
extension DecisionUtility: Sendable {}
extension MufsEventPayload: Sendable {}
extension MpgLevelSummary: Sendable {}
extension MpgSubgraphResponse: Sendable {}
extension SnapshotMpg: Sendable {}
extension SnapshotResponse: Sendable {}
extension SessionSummary: Sendable {}
extension Cohort: Sendable {}
extension NoeticSample: Sendable {}
extension SubjectNoeticSeries: Sendable {}
extension GroupNoeticSample: Sendable {}
extension CohortNoeticSummary: Sendable {}
extension MpgEchoGroup: Sendable {}
extension MpgEchoMember: Sendable {}
extension MpgEchoWindow: Sendable {}
extension ReplayResponse: Sendable {}
extension CohortMpgEchoResponse: Sendable {}
extension MessageType: Sendable {}
extension JSONValue: @unchecked Sendable {}

// MARK: - Cohort / Coherence wall

public struct Cohort: Codable, Hashable, Identifiable {
    public let id: String
    public let name: String
    public let description: String?
    public let memberSessions: [String]
    public let createdUTC: String

    enum CodingKeys: String, CodingKey {
        case id = "cohort_id"
        case name
        case description
        case memberSessions = "member_sessions"
        case createdUTC = "created_utc"
    }
}

public struct NoeticSample: Codable, Hashable {
    public let tRelMs: Int
    public let globalCoherenceScore: Double
    public let entropyChange: Double
    public let bandStrengths: [Double]

    enum CodingKeys: String, CodingKey {
        case tRelMs = "t_rel_ms"
        case globalCoherenceScore = "global_coherence_score"
        case entropyChange = "entropy_change"
        case bandStrengths = "band_strengths"
    }
}

public struct SubjectNoeticSeries: Codable, Hashable, Identifiable {
    public let id: String
    public let subjectLabel: String
    public let samples: [NoeticSample]

    enum CodingKeys: String, CodingKey {
        case id = "session_id"
        case subjectLabel = "subject_label"
        case samples
    }
}

public struct GroupNoeticSample: Codable, Hashable {
    public let tRelMs: Int
    public let meanGlobalCoherence: Double
    public let dispersionGlobalCoherence: Double
    public let bandSyncIndex: [Double]

    enum CodingKeys: String, CodingKey {
        case tRelMs = "t_rel_ms"
        case meanGlobalCoherence = "mean_global_coherence"
        case dispersionGlobalCoherence = "dispersion_global_coherence"
        case bandSyncIndex = "band_sync_index"
    }
}

public struct CohortNoeticSummary: Codable, Hashable {
    public let cohortID: String
    public let members: [SubjectNoeticSeries]
    public let group: [GroupNoeticSample]

    enum CodingKeys: String, CodingKey {
        case cohortID = "cohort_id"
        case members
        case group
    }
}

public struct MpgEchoGroup: Codable, Hashable, Identifiable {
    public let id: String
    public let label: String?
    public let memberSegments: [MpgEchoMember]
    public let consistencyScore: Double
    public let occurrenceWindows: [MpgEchoWindow]

    enum CodingKeys: String, CodingKey {
        case id = "echo_id"
        case label
        case memberSegments = "member_segments"
        case consistencyScore = "consistency_score"
        case occurrenceWindows = "occurrence_windows"
    }
}

public struct MpgEchoMember: Codable, Hashable {
    public let sessionID: String
    public let segmentID: String

    enum CodingKeys: String, CodingKey {
        case sessionID = "session_id"
        case segmentID = "segment_id"
    }
}

public struct MpgEchoWindow: Codable, Hashable {
    public let trialID: String?
    public let tRelMsStart: Int
    public let tRelMsEnd: Int

    enum CodingKeys: String, CodingKey {
        case trialID = "trial_id"
        case tRelMsStart = "t_rel_ms_start"
        case tRelMsEnd = "t_rel_ms_end"
    }
}

public struct CohortMpgEchoResponse: Codable, Hashable {
    public let cohortID: String
    public let echoes: [MpgEchoGroup]

    enum CodingKeys: String, CodingKey {
        case cohortID = "cohort_id"
        case echoes
    }
}
