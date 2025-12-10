import Foundation

// Core types describing the symbiosis domain. Initial scaffold only; not persisted yet.

public struct SymbiosisProfile: Codable, Sendable {
    public var personality: String
    public var goals: [String]
    public var habits: [String]
    public var healthSummary: String
    public var environment: String
    public var communicationStyle: String

    public init(personality: String, goals: [String], habits: [String], healthSummary: String, environment: String, communicationStyle: String) {
        self.personality = personality
        self.goals = goals
        self.habits = habits
        self.healthSummary = healthSummary
        self.environment = environment
        self.communicationStyle = communicationStyle
    }

    public static let empty = SymbiosisProfile(
        personality: "unknown",
        goals: [],
        habits: [],
        healthSummary: "n/a",
        environment: "n/a",
        communicationStyle: "n/a"
    )
}

public struct PersonaLayers: Codable, Sendable {
    public var aToZArchivesFreshness: Double
    public var mentatRepositoryFreshness: Double
    public var secondFoundationDrift: Double
    public var seldonPlanHorizon: String
    public var forceVergenceBalance: Double

    public init(aToZArchivesFreshness: Double, mentatRepositoryFreshness: Double, secondFoundationDrift: Double, seldonPlanHorizon: String, forceVergenceBalance: Double) {
        self.aToZArchivesFreshness = aToZArchivesFreshness
        self.mentatRepositoryFreshness = mentatRepositoryFreshness
        self.secondFoundationDrift = secondFoundationDrift
        self.seldonPlanHorizon = seldonPlanHorizon
        self.forceVergenceBalance = forceVergenceBalance
    }

    public static let stub = PersonaLayers(
        aToZArchivesFreshness: 0.8,
        mentatRepositoryFreshness: 0.6,
        secondFoundationDrift: 0.2,
        seldonPlanHorizon: "30d",
        forceVergenceBalance: 0.7
    )
}

public enum SynapseChannel: String, Codable, Sendable {
    case bio, symbolic, noetic
}

public struct SynapseEvent: Identifiable, Codable, Sendable {
    public let id: UUID
    public let source: String // human|ai
    public let channel: SynapseChannel
    public let message: String
    public let tRelMs: Int

    public init(id: UUID, source: String, channel: SynapseChannel, message: String, tRelMs: Int) {
        self.id = id
        self.source = source
        self.channel = channel
        self.message = message
        self.tRelMs = tRelMs
    }
}

public struct CouncilCase: Codable, Sendable {
    public var topic: String
    public var facts: [String]
    public var options: [String]
}

public struct CouncilResolution: Codable, Sendable {
    public var decision: String
    public var confidence: Double
    public var dissent: Double
    public var rationale: String

    public init(decision: String, confidence: Double, dissent: Double, rationale: String) {
        self.decision = decision
        self.confidence = confidence
        self.dissent = dissent
        self.rationale = rationale
    }

    public static let none = CouncilResolution(decision: "pending", confidence: 0, dissent: 0, rationale: "No decision yet")
}

public struct LoopMetrics: Codable, Sendable {
    public var bioDrift: Double
    public var symbolicDrift: Double
    public var noeticDrift: Double
    public var stability: Double

    public init(bioDrift: Double, symbolicDrift: Double, noeticDrift: Double, stability: Double) {
        self.bioDrift = bioDrift
        self.symbolicDrift = symbolicDrift
        self.noeticDrift = noeticDrift
        self.stability = stability
    }

    public static let stub = LoopMetrics(bioDrift: 0.1, symbolicDrift: 0.2, noeticDrift: 0.15, stability: 0.82)
}

public struct SymbiosisState: Codable, Sendable {
    public var profile: SymbiosisProfile
    public var persona: PersonaLayers
    public var synapseEvents: [SynapseEvent]
    public var lastCouncil: CouncilResolution
    public var loop: LoopMetrics

    public init(profile: SymbiosisProfile, persona: PersonaLayers, synapseEvents: [SynapseEvent], lastCouncil: CouncilResolution, loop: LoopMetrics) {
        self.profile = profile
        self.persona = persona
        self.synapseEvents = synapseEvents
        self.lastCouncil = lastCouncil
        self.loop = loop
    }

    public static let stub = SymbiosisState(
        profile: .empty,
        persona: .stub,
        synapseEvents: [
            SynapseEvent(id: UUID(), source: "human", channel: .symbolic, message: "Adjust goal: focus on recovery", tRelMs: 0),
            SynapseEvent(id: UUID(), source: "ai", channel: .noetic, message: "Suggested plan update", tRelMs: 1000)
        ],
        lastCouncil: .none,
        loop: .stub
    )
}
