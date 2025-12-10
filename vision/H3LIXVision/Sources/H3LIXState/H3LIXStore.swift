import Foundation
import Combine
import H3LIXCore
import H3LIXNet
import SymbiosisCore

@MainActor
public final class H3LIXStore: ObservableObject {
    public enum ConnectionState: Equatable {
        case idle
        case loadingSnapshot(sessionID: String)
        case streaming(sessionID: String)
        case error(String)
    }

    @Published public private(set) var sessions: [SessionSummary] = []
    @Published public private(set) var snapshot: SnapshotResponse?
    @Published public private(set) var somatic: SomaticStatePayload?
    @Published public private(set) var symbolic: SymbolicStatePayload?
    @Published public private(set) var noetic: NoeticStatePayload?
    @Published public private(set) var decisionCycle: DecisionCyclePayload?
    @Published public private(set) var mpg: MpgGraphState = .init()
    @Published public private(set) var rogueEvents: [RogueVariableEventPayload] = []
    @Published public private(set) var mufsEvents: [MufsEventPayload] = []
    @Published public private(set) var connectionState: ConnectionState = .idle
    @Published public private(set) var latestTRelMs: Int = 0
    @Published public private(set) var eventMarkers: [TimelineMarker] = []
    @Published public private(set) var cohorts: [Cohort] = []
    @Published public private(set) var cohortSummary: CohortNoeticSummary?
    @Published public private(set) var cohortEchoes: CohortMpgEchoResponse?
    @Published public private(set) var symbiosis: SymbiosisState = .stub

    private let client: H3LIXClient
    public let scenarioPresets: [ScenarioPreset]
    private var timeReference: Date?
    private let isoFormatter: ISO8601DateFormatter = {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fmt
    }()

    public init(client: H3LIXClient, scenarios: [ScenarioPreset] = ScenarioCatalog.presets) {
        self.client = client
        self.scenarioPresets = scenarios
    }

    // MARK: - Session lifecycle

    public func refreshSessions() {
        Task {
            do {
                sessions = try await client.fetchSessions()
                if sessions.isEmpty {
                    seedDemoSession()
                }
                ensureSymbiosisProfile()
            } catch {
                connectionState = .error("Failed to load sessions: \(error)")
                seedDemoSession()
            }
        }
    }

    public func updateProfile(personality: String? = nil, goals: [String]? = nil, habits: [String]? = nil, healthSummary: String? = nil, environment: String? = nil, communicationStyle: String? = nil) {
        let current = symbiosis.profile
        let updated = SymbiosisProfile(
            personality: personality ?? current.personality,
            goals: goals ?? current.goals,
            habits: habits ?? current.habits,
            healthSummary: healthSummary ?? current.healthSummary,
            environment: environment ?? current.environment,
            communicationStyle: communicationStyle ?? current.communicationStyle
        )
        symbiosis = SymbiosisState(
            profile: updated,
            persona: symbiosis.persona,
            synapseEvents: symbiosis.synapseEvents,
            lastCouncil: symbiosis.lastCouncil,
            loop: symbiosis.loop
        )
        recordSynapseEvent(source: "human", channel: .symbolic, message: "Profile updated")
    }

    public func loadSnapshot(for sessionID: String) {
        print("[H3LIX] loadSnapshot start session=\(sessionID)")
        connectionState = .loadingSnapshot(sessionID: sessionID)
        Task {
            do {
                let snap = try await client.fetchSnapshot(sessionID: sessionID)
                apply(snapshot: snap)
                connectionState = .idle
                print("[H3LIX] loadSnapshot success session=\(sessionID) tRelMs=\(snap.tRelMs) nodes=\(snap.mpg.baseSubgraph.nodes.count)")
            } catch {
                connectionState = .error("Snapshot failed: \(error)")
                print("[H3LIX] loadSnapshot failed session=\(sessionID) error=\(error)")
                if sessionID == "demo-session" {
                    apply(snapshot: MockData.demoSnapshot())
                    connectionState = .idle
                }
            }
        }
    }

    public func startStream(sessionID: String) {
        connectionState = .streaming(sessionID: sessionID)
        recordSynapseEvent(source: "human", channel: .symbolic, message: "Start stream \(sessionID)")
        Task {
            do {
                try await client.openStream(
                    sessionID: sessionID,
                    onEvent: { [weak self] envelope in
                        guard let self else { return }
                        Task { @MainActor in
                            self.apply(envelope: envelope)
                        }
                    },
                    onClose: { [weak self] in
                        guard let self else { return }
                        Task { @MainActor in
                            self.connectionState = .error("Stream closed")
                            self.recordSynapseEvent(source: "ai", channel: .noetic, message: "Stream closed \(sessionID)")
                        }
                    }
                )
            } catch {
                connectionState = .error("Stream failed: \(error)")
                recordSynapseEvent(source: "ai", channel: .noetic, message: "Stream failed \(sessionID)")
            }
        }
    }

    public func stopStream() {
        Task {
            await client.closeStream()
            connectionState = .idle
            recordSynapseEvent(source: "human", channel: .symbolic, message: "Stop stream")
        }
    }

    private func seedDemoSession() {
        let demo = MockData.demoSession()
        sessions = [demo]
        apply(snapshot: MockData.demoSnapshot())
    }

    public func refreshCohorts() {
        Task {
            do {
                cohorts = try await client.listCohorts()
            } catch {
                connectionState = .error("Cohorts failed: \(error)")
            }
        }
    }

    public func loadCohortSummary(cohortID: String, fromMs: Int, toMs: Int, binMs: Int = 1_000) {
        Task {
            do {
                cohortSummary = try await client.fetchCohortNoeticSummary(cohortID: cohortID, fromMs: fromMs, toMs: toMs, binMs: binMs)
            } catch {
                connectionState = .error("Cohort summary failed: \(error)")
            }
        }
    }

    public func loadCohortEchoes(cohortID: String, fromMs: Int, toMs: Int, minConsistency: Double = 0.7) {
        Task {
            do {
                cohortEchoes = try await client.fetchCohortMpgEchoes(cohortID: cohortID, fromMs: fromMs, toMs: toMs, minConsistency: minConsistency)
            } catch {
                connectionState = .error("Echoes failed: \(error)")
            }
        }
    }

    public func fetchReplay(sessionID: String, fromMs: Int, toMs: Int) async throws -> ReplayResponse {
        try await client.fetchReplay(sessionID: sessionID, fromMs: fromMs, toMs: toMs)
    }

    public func applyScenario(_ scenario: ScenarioPreset) {
        apply(snapshot: scenario.snapshot)
        rogueEvents = scenario.rogue.map { [$0] } ?? []
        mufsEvents = scenario.mufs.map { [$0] } ?? []
        eventMarkers.removeAll()
        if let rogue = scenario.rogue {
            appendMarker(.init(id: rogue.rogueID, type: .rogue, tRelMs: scenario.snapshot.tRelMs))
        }
        if let mufs = scenario.mufs {
            appendMarker(.init(id: mufs.mufsID, type: .mufs, tRelMs: scenario.snapshot.tRelMs))
        }
        connectionState = .idle
    }

    // MARK: - Apply updates

    public func apply(snapshot: SnapshotResponse) {
        print("[H3LIX] apply snapshot session=\(snapshot.sessionID) tRelMs=\(snapshot.tRelMs) nodes=\(snapshot.mpg.baseSubgraph.nodes.count) edges=\(snapshot.mpg.baseSubgraph.edges.count) segments=\(snapshot.mpg.baseSubgraph.segments.count)")
        mpg.nodes.removeAll()
        mpg.edges.removeAll()
        mpg.segments.removeAll()
        snapshot.mpg.baseSubgraph.nodes.forEach { mpg.nodes[$0.id] = $0 }
        snapshot.mpg.baseSubgraph.edges.forEach { mpg.edges[$0.id] = $0 }
        snapshot.mpg.baseSubgraph.segments.forEach { mpg.segments[$0.id] = $0 }
        mpg.mpgID = snapshot.mpg.mpgID
        mpg.level = snapshot.mpg.baseSubgraph.level
        mpg.levelSummaries = snapshot.mpg.levelSummaries
        mpg.lastDeltaID = nil

        self.snapshot = snapshot
        somatic = snapshot.somatic
        symbolic = snapshot.symbolic
        noetic = snapshot.noetic
        decisionCycle = snapshot.lastDecisionCycle
        latestTRelMs = snapshot.tRelMs
        timeReference = Date()
        recordSynapseEvent(source: "ai", channel: .symbolic, message: "Snapshot applied \(snapshot.sessionID)")
        updateSymbiosisState()
    }

    public func apply(envelope: AnyTelemetryEnvelope) {
        if timeReference == nil {
            timeReference = isoFormatter.date(from: envelope.timestampUTC)
        }
        updateLatestTime(from: envelope)

        switch envelope.payload {
        case .somatic(let payload):
            somatic = payload
            recordSynapseEvent(source: "human", channel: .bio, message: "Somatic update")
        case .symbolic(let payload):
            symbolic = payload
            recordSynapseEvent(source: "human", channel: .symbolic, message: "Symbolic update")
        case .noetic(let payload):
            noetic = payload
            recordSynapseEvent(source: "ai", channel: .noetic, message: "Noetic update")
        case .decision(let payload):
            decisionCycle = payload
            appendMarker(.init(id: payload.decisionID ?? UUID().uuidString, type: .decision, tRelMs: latestTRelMs))
            recordSynapseEvent(source: "ai", channel: .noetic, message: "Decision phase \(payload.phase)")
        case .mpgDelta(let payload):
            mpg.apply(delta: payload)
            recordSynapseEvent(source: "ai", channel: .symbolic, message: "MPG delta \(payload.deltaID)")
        case .rogueVariable(let payload):
            rogueEvents.insert(payload, at: 0)
            rogueEvents = Array(rogueEvents.prefix(50))
            appendMarker(.init(id: payload.rogueID, type: .rogue, tRelMs: latestTRelMs))
            recordSynapseEvent(source: "ai", channel: .symbolic, message: "Rogue \(payload.rogueID)")
        case .mufs(let payload):
            mufsEvents.insert(payload, at: 0)
            mufsEvents = Array(mufsEvents.prefix(50))
            appendMarker(.init(id: payload.mufsID, type: .mufs, tRelMs: latestTRelMs))
            recordSynapseEvent(source: "ai", channel: .symbolic, message: "MUFS \(payload.mufsID)")
        case .unknown:
            break
        }
        updateSymbiosisState()
    }
}

// MARK: - Visual projections

// MARK: - MPG state

public enum TimelineMarkerType: String {
    case rogue
    case mufs
    case decision
}

public struct TimelineMarker: Identifiable {
    public let id: String
    public let type: TimelineMarkerType
    public let tRelMs: Int
}

public struct MpgGraphState {
    public var mpgID: String?
    public var level: Int = 0
    public var levelSummaries: [MpgLevelSummary] = []
    public var nodes: [String: MpgNode] = [:]
    public var edges: [String: MpgEdge] = [:]
    public var segments: [String: MpgSegment] = [:]
    public var lastDeltaID: String?

    public init() {}

    public mutating func apply(delta: MpgDeltaPayload) {
        mpgID = delta.mpgID
        level = delta.level
        lastDeltaID = delta.deltaID

        for op in delta.operations {
            switch op.kind {
            case .addNode:
                if let node = op.node { nodes[node.id] = node }
            case .updateNode:
                if let node = op.node {
                    nodes[node.id] = node
                } else if let nodeID = op.nodeID, let patch = op.patch {
                    nodes[nodeID] = merge(node: nodes[nodeID], with: patch)
                }
            case .addEdge:
                if let edge = op.edge { edges[edge.id] = edge }
            case .updateEdge:
                if let edge = op.edge {
                    edges[edge.id] = edge
                } else if let edgeID = op.edgeID, let patch = op.patch {
                    edges[edgeID] = merge(edge: edges[edgeID], with: patch)
                }
            case .addSegment:
                if let segment = op.segment { segments[segment.id] = segment }
            case .updateSegment:
                if let segment = op.segment {
                    segments[segment.id] = segment
                } else if let segmentID = op.segmentID, let patch = op.patch {
                    segments[segmentID] = merge(segment: segments[segmentID], with: patch)
                }
            }
        }
    }

    private func merge(node: MpgNode?, with patch: [String: JSONValue]) -> MpgNode? {
        guard let node = node else { return nil }
        let label = patch["label"]?.stringValue ?? node.label
        let desc = patch["description"]?.stringValue ?? node.description
        let confidence = patch["confidence"]?.numberValue ?? node.confidence
        let importance = patch["importance"]?.numberValue ?? node.importance
        let roles = patch["roles"]?.stringArray ?? node.roles

        let metrics = mergeMetrics(current: node.metrics, patch: patch["metrics"]?.objectValue)

        return makeNode(
            id: node.id,
            label: label,
            description: desc,
            layerTags: node.layerTags,
            metrics: metrics,
            confidence: confidence,
            importance: importance,
            roles: roles,
            evidencePreview: node.evidencePreview,
            reasoningProvenance: node.reasoningProvenance,
            fallback: node
        )
    }

    private func merge(edge: MpgEdge?, with patch: [String: JSONValue]) -> MpgEdge? {
        guard let edge = edge else { return nil }
        let strength = patch["strength"]?.numberValue ?? edge.strength
        let confidence = patch["confidence"]?.numberValue ?? edge.confidence
        return makeEdge(
            id: edge.id,
            source: edge.source,
            target: edge.target,
            type: edge.type,
            strength: strength,
            confidence: confidence,
            fallback: edge
        )
    }

    private func merge(segment: MpgSegment?, with patch: [String: JSONValue]) -> MpgSegment? {
        guard let segment = segment else { return nil }
        let cohesion = patch["cohesion"]?.numberValue ?? segment.cohesion
        let avgImp = patch["average_importance"]?.numberValue ?? segment.averageImportance
        let avgConf = patch["average_confidence"]?.numberValue ?? segment.averageConfidence
        return makeSegment(
            id: segment.id,
            label: segment.label,
            level: segment.level,
            memberNodeIds: segment.memberNodeIds,
            cohesion: cohesion,
            averageImportance: avgImp,
            averageConfidence: avgConf,
            affectiveLoad: segment.affectiveLoad ?? 0.0,
            fallback: segment
        )
    }

    private func mergeMetrics(current: MpgNodeMetrics, patch: [String: JSONValue]?) -> MpgNodeMetrics {
        guard let metricsPatch = patch else { return current }
        let valence = metricsPatch["valence"]?.numberValue ?? current.valence
        let intensity = metricsPatch["intensity"]?.numberValue ?? current.intensity
        let recency = metricsPatch["recency"]?.numberValue ?? current.recency
        let stability = metricsPatch["stability"]?.numberValue ?? current.stability
        return makeMetrics(valence: valence, intensity: intensity, recency: recency, stability: stability, fallback: current)
    }
}

// MARK: - Helpers

private extension H3LIXStore {
    func updateLatestTime(from envelope: AnyTelemetryEnvelope) {
        if let tRel = payloadTRelMs(from: envelope.payload) {
            latestTRelMs = max(latestTRelMs, tRel)
            return
        }
        if let reference = timeReference, let date = isoFormatter.date(from: envelope.timestampUTC) {
            let ms = Int(date.timeIntervalSince(reference) * 1000)
            latestTRelMs = max(latestTRelMs, ms)
        }
    }

    func payloadTRelMs(from payload: TelemetryPayload) -> Int? {
        switch payload {
        case .somatic(let p): return p.tRelMs
        case .symbolic(let p): return p.tRelMs
        case .noetic(let p): return p.tRelMs
        case .decision: return nil
        case .mpgDelta: return nil
        case .rogueVariable, .mufs: return nil
        case .unknown: return nil
        }
    }

    func appendMarker(_ marker: TimelineMarker) {
        eventMarkers.insert(marker, at: 0)
        eventMarkers = Array(eventMarkers.prefix(100))
    }

    public func mergedMetrics(current: MpgNodeMetrics, patch: [String: JSONValue]?) -> MpgNodeMetrics {
        guard let metricsPatch = patch else { return current }
        let valence = metricsPatch["valence"]?.numberValue ?? current.valence
        let intensity = metricsPatch["intensity"]?.numberValue ?? current.intensity
        let recency = metricsPatch["recency"]?.numberValue ?? current.recency
        let stability = metricsPatch["stability"]?.numberValue ?? current.stability
        return makeMetrics(valence: valence, intensity: intensity, recency: recency, stability: stability, fallback: current)
    }
}

extension Collection where Element == Double {
    var average: Double {
        guard !isEmpty else { return 0 }
        return reduce(0, +) / Double(count)
    }
}

private extension JSONValue {
    var stringValue: String? {
        if case .string(let value) = self { return value }
        return nil
    }

    var numberValue: Double? {
        if case .number(let value) = self { return value }
        return nil
    }

    var objectValue: [String: JSONValue]? {
        if case .object(let dict) = self { return dict }
        return nil
    }

    var stringArray: [String]? {
        if case .array(let values) = self {
            return values.compactMap { $0.stringValue }
        }
        return nil
    }
}

// MARK: - Factories for Core types (memberwise initializers not public)

private struct MetricsDTO: Codable {
    let valence: Double
    let intensity: Double
    let recency: Double
    let stability: Double
}

private struct NodeDTO: Codable {
    let id: String
    let label: String
    let description: String?
    let layerTags: [String]
    let metrics: MpgNodeMetrics
    let confidence: Double
    let importance: Double
    let roles: [String]
    let evidencePreview: [MpgEvidencePreview]
    let reasoningProvenance: String?
}

private struct EdgeDTO: Codable {
    let id: String
    let source: String
    let target: String
    let type: String
    let strength: Double
    let confidence: Double
}

private struct SegmentDTO: Codable {
    let id: String
    let label: String
    let level: Int
    let memberNodeIds: [String]
    let cohesion: Double
    let averageImportance: Double
    let averageConfidence: Double
    let affectiveLoad: Double
}

private func makeMetrics(valence: Double, intensity: Double, recency: Double, stability: Double, fallback: MpgNodeMetrics) -> MpgNodeMetrics {
    let dto = MetricsDTO(valence: valence, intensity: intensity, recency: recency, stability: stability)
    if let data = try? JSONEncoder().encode(dto),
       let decoded = try? JSONDecoder().decode(MpgNodeMetrics.self, from: data) {
        return decoded
    }
    return fallback
}

private func makeNode(
    id: String,
    label: String,
    description: String?,
    layerTags: [String],
    metrics: MpgNodeMetrics,
    confidence: Double,
    importance: Double,
    roles: [String],
    evidencePreview: [MpgEvidencePreview],
    reasoningProvenance: String?,
    fallback: MpgNode
) -> MpgNode {
    let dto = NodeDTO(
        id: id,
        label: label,
        description: description,
        layerTags: layerTags,
        metrics: metrics,
        confidence: confidence,
        importance: importance,
        roles: roles,
        evidencePreview: evidencePreview,
        reasoningProvenance: reasoningProvenance
    )
    if let data = try? JSONEncoder().encode(dto),
       let decoded = try? JSONDecoder().decode(MpgNode.self, from: data) {
        return decoded
    }
    return fallback
}

private func makeEdge(id: String, source: String, target: String, type: String, strength: Double, confidence: Double, fallback: MpgEdge) -> MpgEdge {
    let dto = EdgeDTO(id: id, source: source, target: target, type: type, strength: strength, confidence: confidence)
    if let data = try? JSONEncoder().encode(dto),
       let decoded = try? JSONDecoder().decode(MpgEdge.self, from: data) {
        return decoded
    }
    return fallback
}

private func makeSegment(
    id: String,
    label: String,
    level: Int,
    memberNodeIds: [String],
    cohesion: Double,
    averageImportance: Double,
    averageConfidence: Double,
    affectiveLoad: Double,
    fallback: MpgSegment
) -> MpgSegment {
    let dto = SegmentDTO(
        id: id,
        label: label,
        level: level,
        memberNodeIds: memberNodeIds,
        cohesion: cohesion,
        averageImportance: averageImportance,
        averageConfidence: averageConfidence,
        affectiveLoad: affectiveLoad
    )
    if let data = try? JSONEncoder().encode(dto),
       let decoded = try? JSONDecoder().decode(MpgSegment.self, from: data) {
        return decoded
    }
    return fallback
}

// MARK: - Symbiosis derivation (stub)
extension H3LIXStore {
    private func updateSymbiosisState() {
        // Derive simple freshness metrics from available telemetry.
        let somaticScore = clamp(somatic?.features.values.average, min: 0, max: 1)
        let symbolicScore = clamp(symbolic?.beliefs.map(\.confidence).average, min: 0, max: 1)
        let noeticScore = clamp(noetic?.globalCoherenceScore ?? 0, min: 0, max: 1)
        let mpgDensity = clamp(Double(mpg.nodes.count) / 100.0, min: 0, max: 1)
        let rogueCount = clamp(Double(rogueEvents.count) / 10.0, min: 0, max: 1)
        let mufsCount = clamp(Double(mufsEvents.count) / 10.0, min: 0, max: 1)

        let persona = PersonaLayers(
            aToZArchivesFreshness: 0.5 + symbolicScore * 0.5,
            mentatRepositoryFreshness: 0.5 + somaticScore * 0.5,
            secondFoundationDrift: 1 - mpgDensity * 0.5,
            seldonPlanHorizon: "30d",
            forceVergenceBalance: (somaticScore + symbolicScore + noeticScore) / 3.0
        )

        var synEvents = symbiosis.synapseEvents
        if let dec = decisionCycle?.phase {
            let evt = SynapseEvent(id: UUID(), source: "ai", channel: .noetic, message: "Decision phase: \(dec)", tRelMs: latestTRelMs)
            synEvents.insert(evt, at: 0)
            synEvents = Array(synEvents.prefix(10))
        }

        let decisionConfidence = clamp(decisionCycle?.consequenceOutcome?.metrics["confidence"], min: 0, max: 1)
        let rationale = decisionCycle?.consequenceOutcome?.label ?? decisionCycle?.responseAction?.label ?? decisionCycle?.phase ?? "Awaiting decision"

        let loop = LoopMetrics(
            bioDrift: clamp(somaticScore, min: 0, max: 1),
            symbolicDrift: clamp(symbolicScore, min: 0, max: 1),
            noeticDrift: clamp(noeticScore, min: 0, max: 1),
            stability: clamp(1 - abs((noetic?.entropyChange ?? 0) / 3.0) - 0.1 * (rogueCount + mufsCount), min: 0, max: 1)
        )

        let council = CouncilResolution(
            decision: decisionCycle?.phase ?? "pending",
            confidence: decisionConfidence,
            dissent: clamp(1 - decisionConfidence, min: 0, max: 1),
            rationale: rationale
        )

        symbiosis = SymbiosisState(
            profile: symbiosis.profile, // still stubbed
            persona: persona,
            synapseEvents: synEvents,
            lastCouncil: council,
            loop: loop
        )
    }

    private func ensureSymbiosisProfile() {
        if symbiosis.profile.personality != "unknown" { return }
        let goal = sessions.first?.experimentID ?? "demo"
        let profile = SymbiosisProfile(
            personality: "adaptive",
            goals: [goal],
            habits: [],
            healthSummary: "baseline",
            environment: "simulator",
            communicationStyle: "concise"
        )
        symbiosis = SymbiosisState(
            profile: profile,
            persona: symbiosis.persona,
            synapseEvents: symbiosis.synapseEvents,
            lastCouncil: symbiosis.lastCouncil,
            loop: symbiosis.loop
        )
    }

    private func recordSynapseEvent(source: String, channel: SynapseChannel, message: String) {
        var events = symbiosis.synapseEvents
        events.insert(SynapseEvent(id: UUID(), source: source, channel: channel, message: message, tRelMs: latestTRelMs), at: 0)
        events = Array(events.prefix(15))
        symbiosis = SymbiosisState(
            profile: symbiosis.profile,
            persona: symbiosis.persona,
            synapseEvents: events,
            lastCouncil: symbiosis.lastCouncil,
            loop: symbiosis.loop
        )
    }

    private func clamp<T: Comparable & BinaryFloatingPoint>(_ value: T?, min: T, max: T) -> T {
        guard let v = value else { return min }
        if v < min { return min }
        if v > max { return max }
        return v
    }
}
