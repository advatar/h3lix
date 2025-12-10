import Foundation
import simd
import H3LIXCore
import H3LIXState

public struct HelixRibbonState: Equatable, Sendable {
    public var activity: Float      // 0...1
    public var anomaly: Float       // 0...1
    public var uncertainty: Float   // 0...1
}

public struct HelixVisualState: Equatable, Sendable {
    public var timePlaneHeight: Float   // 0...1
    public var somatic: HelixRibbonState
    public var symbolic: HelixRibbonState
    public var noetic: HelixRibbonState
}

public struct HaloBandState: Equatable, Sendable {
    public var intensity: Float   // 0...1
    public var turbulence: Float  // 0...1
}

public struct HaloVisualState: Equatable, Sendable {
    public var globalCoherence: Float   // 0...1
    public var bands: [HaloBandState]
    public var pulse: Float             // 0...1 intuitive accuracy pulse
}

public struct MpgNodeInstance: Equatable, Identifiable, Sendable {
    public let id: String
    public var position: SIMD3<Float>
    public var importance: Float
    public var confidence: Float
    public var valence: Float      // -1...1
    public var stability: Float
    public var isRogueHotspot: Bool
    public var isMufsElement: Bool
}

public struct MpgEdgeInstance: Equatable, Identifiable, Sendable {
    public let id: String
    public var fromIndex: Int
    public var toIndex: Int
    public var strength: Float
    public var typeIndex: Int
}

public struct MpgVisualState: Equatable, Sendable {
    public var level: Int
    public var nodes: [MpgNodeInstance]
    public var edges: [MpgEdgeInstance]
}

public struct SorkPhaseState: Equatable, Sendable {
    public var active: Bool
    public var intensity: Float    // 0...1
}

public struct SorkVisualState: Equatable, Sendable {
    public var cometAngle: Float   // radians
    public var phases: [SorkPhaseState] // S,O,R,K,N,S'
}

public struct RogueOverlayState: Equatable, Sendable {
    public var activeSegmentIds: [String]
}

public struct MufsOverlayState: Equatable, Sendable {
    public var hasMufs: Bool
    public var affectedNodeIds: [String]
}

public struct VisualSnapshot: Equatable, Sendable {
    public var helix: HelixVisualState
    public var halo: HaloVisualState
    public var mpg: MpgVisualState
    public var sork: SorkVisualState
    public var rogue: RogueOverlayState?
    public var mufs: MufsOverlayState?
    public var wall: CoherenceWallVisual

    public static let empty: VisualSnapshot = VisualSnapshot(
        helix: .init(
            timePlaneHeight: 0.5,
            somatic: .init(activity: 0, anomaly: 0, uncertainty: 0),
            symbolic: .init(activity: 0, anomaly: 0, uncertainty: 0),
            noetic: .init(activity: 0, anomaly: 0, uncertainty: 0)
        ),
        halo: .init(globalCoherence: 0, bands: [], pulse: 0),
        mpg: .init(level: 0, nodes: [], edges: []),
        sork: .init(cometAngle: 0, phases: [
            .init(active: true, intensity: 0.1),
            .init(active: false, intensity: 0),
            .init(active: false, intensity: 0),
            .init(active: false, intensity: 0),
            .init(active: false, intensity: 0),
            .init(active: false, intensity: 0)
        ]),
        rogue: nil,
        mufs: nil,
        wall: .init(subjects: [], groupRibbon: .init(samples: []), currentTRelMs: 0)
    )
}
