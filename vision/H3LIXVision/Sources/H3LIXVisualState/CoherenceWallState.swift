import Foundation
import simd
import H3LIXCore

public struct SubjectColumnVisual: Identifiable, Equatable, Sendable {
    public let id: String
    public let label: String
    public let samples: [NoeticSample]
    public let color: SIMD3<Float>
    public let echoWindows: [MpgEchoWindow]
}

public struct GroupRibbonVisual: Equatable, Sendable {
    public let samples: [GroupNoeticSample]
}

public struct CoherenceWallVisual: Equatable, Sendable {
    public let subjects: [SubjectColumnVisual]
    public let groupRibbon: GroupRibbonVisual
    public let currentTRelMs: Int?
}

public enum EchoMarker: Equatable, Identifiable, Sendable {
    case mpgEcho(echoID: String, members: [MpgEchoMember])

    public var id: String {
        switch self {
        case .mpgEcho(let echoID, _): return echoID
        }
    }
}
