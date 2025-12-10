import Foundation
import simd
import H3LIXCore
import H3LIXState

enum VisualMappings {
    static func clamp(_ value: Double, min minValue: Double = 0, max maxValue: Double = 1) -> Double {
        Swift.max(minValue, Swift.min(maxValue, value))
    }

    static func clamp(_ value: Float, min minValue: Float = 0, max maxValue: Float = 1) -> Float {
        Swift.max(minValue, Swift.min(maxValue, value))
    }

    static func smoothStep(_ from: Float, _ to: Float, alpha: Float) -> Float {
        from + (to - from) * alpha
    }

    static func normalizeActivity(_ values: [Double], scale: Double = 1.0) -> Float {
        guard !values.isEmpty else { return 0 }
        let mean = values.reduce(0, +) / Double(values.count)
        let normalized = clamp(mean * scale, max: 1)
        return Float(normalized)
    }

    static func anomaly(_ score: Double?, changePoint: Bool) -> Float {
        let s = clamp((score ?? 0) / 5.0, max: 1)
        return Float(changePoint ? max(0.6, s) : s)
    }

    static func timePlaneHeight(tRelMs: Int?) -> Float {
        guard let t = tRelMs else { return 0.5 }
        let phase = (Double(t % 8_000) / 8_000.0) * (2 * Double.pi)
        return Float(0.5 + 0.25 * sin(phase))
    }

    static func haloBands(from spectrum: [NoeticSpectrumBand], entropyChange: Double) -> [HaloBandState] {
        let entropy = clamp(abs(entropyChange) / 3.0, max: 1)
        return spectrum.prefix(5).map { band in
            let intensity = clamp(band.coherenceStrength, max: 1)
            return HaloBandState(intensity: Float(intensity), turbulence: Float(entropy))
        }
    }

    static func cometAngle(for phase: String, previousAngle: Float) -> Float {
        let mapping: [String: Float] = [
            "S": 0,
            "O": .pi / 3,
            "R": 2 * .pi / 3,
            "K": .pi,
            "N": 4 * .pi / 3,
            "S_prime": 5 * .pi / 3
        ]
        let target = mapping[phase] ?? previousAngle
        return smoothStep(previousAngle, target, alpha: 0.25)
    }

    static func sorkPhases(active phase: String?) -> [SorkPhaseState] {
        let phases = ["S", "O", "R", "K", "N", "S_prime"]
        return phases.map { label in
            let active = label == phase
            return SorkPhaseState(active: active, intensity: active ? 1 : 0.1)
        }
    }

    static func mpgVisual(from graph: MpgGraphState, rogue: RogueOverlayState?, mufs: MufsOverlayState?) -> MpgVisualState {
        let nodes = Array(graph.nodes.values)
        let nodeInstances: [MpgNodeInstance] = nodes.enumerated().map { index, node in
            let position = layoutPosition(for: node, index: index, total: nodes.count, level: graph.level)
            let importance = Float(clamp(node.importance, max: 1))
            let confidence = Float(clamp(node.confidence, max: 1))
            let valence = Float(clamp(node.metrics.valence, min: -1, max: 1))
            let stability = Float(clamp(node.metrics.stability, max: 1))
            let rogueHotspot = isNodeRogue(node: node, segments: graph.segments, overlay: rogue)
            let isMufs = mufs?.affectedNodeIds.contains(node.id) ?? false
            return MpgNodeInstance(
                id: node.id,
                position: position,
                importance: importance,
                confidence: confidence,
                valence: valence,
                stability: stability,
                isRogueHotspot: rogueHotspot,
                isMufsElement: isMufs
            )
        }

        var nodeIndex: [String: Int] = [:]
        for (idx, node) in nodeInstances.enumerated() {
            nodeIndex[node.id] = idx
        }

        let edges = graph.edges.values.compactMap { edge -> MpgEdgeInstance? in
            guard let from = nodeIndex[edge.source], let to = nodeIndex[edge.target] else { return nil }
            let strength = Float(clamp(edge.strength, max: 1))
            let typeIndex = typeIndexForEdge(edge.type)
            return MpgEdgeInstance(id: edge.id, fromIndex: from, toIndex: to, strength: strength, typeIndex: typeIndex)
        }

        return MpgVisualState(level: graph.level, nodes: nodeInstances, edges: edges)
    }

    static func wallVisual(from summary: CohortNoeticSummary?, echoes: CohortMpgEchoResponse?, currentTRelMs: Int?) -> CoherenceWallVisual {
        guard let summary else {
            return CoherenceWallVisual(subjects: [], groupRibbon: GroupRibbonVisual(samples: []), currentTRelMs: currentTRelMs)
        }

        var echoWindowsBySession: [String: [MpgEchoWindow]] = [:]
        if let echoGroups = echoes?.echoes {
            for echo in echoGroups {
                for member in echo.memberSegments {
                    echoWindowsBySession[member.sessionID, default: []].append(contentsOf: echo.occurrenceWindows)
                }
            }
        }

        let palette: [SIMD3<Float>] = [
            SIMD3<Float>(0.9, 0.6, 0.2),
            SIMD3<Float>(0.2, 0.7, 0.9),
            SIMD3<Float>(0.7, 0.5, 0.95),
            SIMD3<Float>(0.95, 0.4, 0.4),
            SIMD3<Float>(0.4, 0.9, 0.6)
        ]

        let subjects = summary.members.enumerated().map { idx, member in
            SubjectColumnVisual(
                id: member.id,
                label: member.subjectLabel,
                samples: member.samples,
                color: palette[idx % palette.count],
                echoWindows: echoWindowsBySession[member.id] ?? []
            )
        }

        let groupRibbon = GroupRibbonVisual(samples: summary.group)

        // Echo markers currently unused in visual; reserved for future overlays.
        _ = echoes

        return CoherenceWallVisual(subjects: subjects, groupRibbon: groupRibbon, currentTRelMs: currentTRelMs)
    }

    // MARK: - Helpers

    private static func layoutPosition(for node: MpgNode, index: Int, total: Int, level: Int) -> SIMD3<Float> {
        // Deterministic pseudo-random radial layout to keep nodes stable between updates.
        let baseAngle = hashToUnit(node.id) * 2 * Float.pi
        let t = total > 0 ? Float(index) / Float(max(total - 1, 1)) : 0
        let radius = 1.0 + Float(level) * 0.25 + Float(node.importance) * 0.6
        let x = cos(baseAngle + t) * radius
        let z = sin(baseAngle + t) * radius
        let y = 0.05 + Float(node.metrics.recency) * 0.2
        return SIMD3<Float>(x, y, z)
    }

    private static func hashToUnit(_ string: String) -> Float {
        var hasher = Hasher()
        hasher.combine(string)
        let value = hasher.finalize()
        let positive = abs(Float(value % 10_000))
        return (positive.truncatingRemainder(dividingBy: 10_000)) / 10_000
    }

    private static func typeIndexForEdge(_ type: String) -> Int {
        abs(type.hashValue) % 6
    }

    private static func isNodeRogue(node: MpgNode, segments: [String: MpgSegment], overlay: RogueOverlayState?) -> Bool {
        guard let overlay else { return false }
        for segmentID in overlay.activeSegmentIds {
            guard let segment = segments[segmentID] else { continue }
            if segment.memberNodeIds.contains(node.id) { return true }
        }
        return false
    }
}
