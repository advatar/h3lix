
import Foundation
import RealityKit
import UIKit
import H3LIXVisualState
import H3LIXCore

@available(visionOS 1.0, *)
public final class CoherenceWallEntity: Entity {
    private var subjectColumns: [String: SubjectColumnEntity] = [:]
    private let groupRibbon = GroupCoherenceRibbonEntity()
    private let arcRadius: Float = 2.5

    public required init() {
        super.init()
        build()
    }

    public required init(from decoder: Decoder) throws {
        super.init()
        build()
    }

    private func build() {
        addChild(groupRibbon)
    }

    public func apply(_ visual: CoherenceWallVisual) {
        let count = max(visual.subjects.count, 1)
        for (index, subject) in visual.subjects.enumerated() {
            let angle = (-Float.pi / 3) + (Float(index) / Float(max(count - 1, 1))) * (2 * Float.pi / 3)
            let pos = SIMD3<Float>(sin(angle) * arcRadius, 1.4, cos(angle) * arcRadius)
            let column: SubjectColumnEntity
            if let existing = subjectColumns[subject.id] {
                column = existing
            } else {
                column = SubjectColumnEntity()
                column.components.set(SelectableComponent(selection: .cohortSubject(sessionId: subject.id)))
                subjectColumns[subject.id] = column
                addChild(column)
            }
            column.position = pos
            column.look(at: .zero, from: pos, relativeTo: nil)
            column.apply(subject, currentTRelMs: visual.currentTRelMs)
        }

        // Remove stale columns
        let ids = Set(visual.subjects.map(\.id))
        for (id, entity) in subjectColumns where !ids.contains(id) {
            entity.removeFromParent()
            subjectColumns[id] = nil
        }

        groupRibbon.apply(samples: visual.groupRibbon.samples, currentTRelMs: visual.currentTRelMs)
        groupRibbon.position = SIMD3<Float>(0, 2.2, -arcRadius * 0.2)
    }
}

@available(visionOS 1.0, *)
final class SubjectColumnEntity: Entity {
    private let helix = MiniHelixEntity()
    private let strip = CoherenceStripEntity()

    required init() {
        super.init()
        build()
    }

    required init(from decoder: Decoder) throws {
        super.init()
        build()
    }

    private func build() {
        helix.position = SIMD3<Float>(0, 0.5, 0)
        strip.position = SIMD3<Float>(0, 0, 0)
        addChild(helix)
        addChild(strip)
    }

    func apply(_ subject: SubjectColumnVisual, currentTRelMs: Int?) {
        helix.apply(color: subject.color, coherence: subject.samples.last?.globalCoherenceScore ?? 0, entropy: subject.samples.last?.entropyChange ?? 0)
        strip.apply(samples: subject.samples, color: subject.color, currentTRelMs: currentTRelMs, echoWindows: subject.echoWindows)
    }
}

@available(visionOS 1.0, *)
final class MiniHelixEntity: Entity {
    private var strands: [ModelEntity] = []

    required override init() {
        super.init()
        build()
    }

    required init(from decoder: Decoder) throws {
        super.init()
        build()
    }

    private func build() {
        let strandCount = 3
        let segments = 16
        let radius: Float = 0.08
        let height: Float = 0.3
        for s in 0..<strandCount {
            let color = UIColor(hue: CGFloat(Double(s) / 3.0), saturation: 0.7, brightness: 0.9, alpha: 0.9)
            for i in 0..<segments {
                let t = Float(i) / Float(max(segments - 1, 1))
                let angle = t * 3.5 * .pi * 2 + Float(s) * (.pi * 2 / Float(strandCount))
                let x = cos(angle) * radius
                let z = sin(angle) * radius
                let y = (t - 0.5) * height
                let bead = ModelEntity(mesh: .generateSphere(radius: 0.01))
                bead.model?.materials = [SimpleMaterial(color: color, roughness: 0.2, isMetallic: false)]
                bead.position = SIMD3<Float>(x, y, z)
                addChild(bead)
                strands.append(bead)
            }
        }
    }

    func apply(color: SIMD3<Float>, coherence: Double, entropy: Double) {
        let brightness = CGFloat(min(1, 0.3 + coherence * 0.6))
        let alpha = CGFloat(min(1, 0.5 + abs(entropy) * 0.2))
        let uiColor = UIColor(red: CGFloat(color.x), green: CGFloat(color.y), blue: CGFloat(color.z), alpha: alpha).withAlphaComponent(alpha)
        let material = SimpleMaterial(color: uiColor.withAlphaComponent(alpha), roughness: 0.2, isMetallic: false)
        for bead in strands {
            bead.model?.materials = [material]
            bead.scale = SIMD3<Float>(repeating: 0.9 + Float(coherence) * 0.2)
        }
    }
}

@available(visionOS 1.0, *)
final class CoherenceStripEntity: Entity {
    private var quads: [ModelEntity] = []
    private let maxBins = 64

    required override init() {
        super.init()
        build()
    }

    required init(from decoder: Decoder) throws {
        super.init()
        build()
    }

    private func build() {
        for i in 0..<maxBins {
            let quad = ModelEntity(mesh: .generatePlane(width: 0.08, depth: 0.02))
            quad.position = SIMD3<Float>(0, Float(i) * 0.02, 0)
            quads.append(quad)
            addChild(quad)
        }
    }

    func apply(samples: [NoeticSample], color: SIMD3<Float>, currentTRelMs: Int?, echoWindows: [MpgEchoWindow]) {
        let slice = samples.suffix(maxBins)
        let cursorIndex: Int?
        if let current = currentTRelMs, let nearest = slice.enumerated().min(by: { abs($0.element.tRelMs - current) < abs($1.element.tRelMs - current) })?.offset {
            cursorIndex = nearest
        } else {
            cursorIndex = nil
        }
        for (i, sample) in slice.enumerated() {
            let hueColor = UIColor(red: CGFloat(color.x), green: CGFloat(color.y), blue: CGFloat(color.z), alpha: 0.7)
            let brightness = CGFloat(min(1, sample.globalCoherenceScore))
            var alpha = 0.3 + brightness * 0.6
            if let cursor = cursorIndex, cursor == i {
                alpha = min(1, alpha + 0.2)
            }
            if echoWindows.contains(where: { window in sample.tRelMs >= window.tRelMsStart && sample.tRelMs <= window.tRelMsEnd }) {
                alpha = min(1, alpha + 0.2)
            }
            let mat = SimpleMaterial(color: hueColor.withAlphaComponent(alpha), roughness: 0.4, isMetallic: false)
            if i < quads.count {
                quads[i].model?.materials = [mat]
            }
        }
    }
}

@available(visionOS 1.0, *)
final class GroupCoherenceRibbonEntity: Entity {
    private var samples: [GroupNoeticSample] = []
    private let maxBins = 128
    private let ribbon: ModelEntity

    required override init() {
        ribbon = ModelEntity(mesh: .generatePlane(width: 2.4, depth: 0.08))
        super.init()
        build()
    }

    required init(from decoder: Decoder) throws {
        ribbon = ModelEntity(mesh: .generatePlane(width: 2.4, depth: 0.08))
        super.init()
        build()
    }

    private func build() {
        ribbon.model?.materials = [SimpleMaterial(color: UIColor.systemTeal.withAlphaComponent(0.2), roughness: 0.25, isMetallic: false)]
        ribbon.components.set(SelectableComponent(selection: .cohortGroup))
        addChild(ribbon)
    }

    func apply(samples: [GroupNoeticSample], currentTRelMs: Int?) {
        self.samples = Array(samples.suffix(maxBins))
        // Simple emissive pulse based on last sample; full gradient could be added later.
        if let last = self.samples.last {
            let alpha = CGFloat(min(1, 0.2 + last.meanGlobalCoherence * 0.7))
            let color = UIColor.systemTeal.withAlphaComponent(alpha)
            ribbon.model?.materials = [SimpleMaterial(color: color, roughness: 0.2, isMetallic: false)]
        }
        // Cursor indicator (scale) if current time matches
        if let current = currentTRelMs, let nearest = self.samples.min(by: { abs($0.tRelMs - current) < abs($1.tRelMs - current) }) {
            let pulse = Float(min(1.2, 1.0 + nearest.meanGlobalCoherence * 0.2))
            ribbon.scale = SIMD3<Float>(repeating: pulse)
            let syncAvg = nearest.bandSyncIndex.isEmpty ? 0.0 : nearest.bandSyncIndex.reduce(0, +) / Double(nearest.bandSyncIndex.count)
            ribbon.model?.materials = [SimpleMaterial(color: UIColor.systemTeal.withAlphaComponent(CGFloat(0.2 + nearest.meanGlobalCoherence * 0.6)), roughness: 0.2, isMetallic: false)]
            ribbon.orientation = simd_quatf(angle: sin(Float(syncAvg)) * 0.02, axis: SIMD3<Float>(0, 1, 0))
        }
    }
}
