import Foundation

public enum HelixLayerType: String, Codable, CaseIterable {
    case somatic
    case symbolic
    case noetic
}

public enum SorkPhase: String, Codable, CaseIterable {
    case S, O, R, K, N, SPrime
}

public enum H3LIXSelection: Equatable {
    case none
    case mpgNode(nodeId: String)
    case mpgSegment(segmentId: String)
    case rogueCluster(segmentId: String)
    case mufsDecision(decisionId: String)
    case helixLayer(layer: HelixLayerType)
    case sorkPhase(phase: SorkPhase)
    case cohortSubject(sessionId: String)
    case cohortGroup
}

public enum H3LIXMode: Equatable {
    case live
    case replay
    case rogueInspect(rogueId: String)
    case mufsInspect(decisionId: String)
}

@MainActor
public final class H3LIXInteractionModel: ObservableObject {
    @Published public var selection: H3LIXSelection = .none
    @Published public var mode: H3LIXMode = .live
    @Published public var wallVisible: Bool = true

    public init() {}

    public func select(_ selection: H3LIXSelection) {
        self.selection = selection
    }

    public func setMode(_ mode: H3LIXMode) {
        self.mode = mode
    }

    public func toggleWall() {
        wallVisible.toggle()
    }
}
