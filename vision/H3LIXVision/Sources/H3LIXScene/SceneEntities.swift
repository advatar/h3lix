import Foundation
import RealityKit
import UIKit
import Combine
import H3LIXCore
import H3LIXState
import H3LIXVisualState

// MARK: - Helix ribbons

@available(visionOS 1.0, *)
final class RibbonEntity: Entity {
    enum Layer {
        case somatic, symbolic, noetic

        var baseColor: UIColor {
            switch self {
            case .somatic: return UIColor(red: 0.13, green: 0.82, blue: 0.92, alpha: 1.0)
            case .symbolic: return UIColor(red: 0.98, green: 0.65, blue: 0.20, alpha: 1.0)
            case .noetic: return UIColor(red: 0.65, green: 0.50, blue: 0.98, alpha: 1.0)
            }
        }
    }

    private let layer: Layer
    private var segments: [ModelEntity] = []
    private var basePositions: [SIMD3<Float>] = []
    private let segmentCount: Int
    private let radius: Float
    private let height: Float
    private let twist: Float

    init(layer: Layer, segmentCount: Int = 64, radius: Float = 0.25, height: Float = 1.4, twist: Float = 4.5) {
        self.layer = layer
        self.segmentCount = segmentCount
        self.radius = radius
        self.height = height
        self.twist = twist
        super.init()
        build()
    }

    required init() {
        self.layer = .somatic
        self.segmentCount = 64
        self.radius = 0.25
        self.height = 1.4
        self.twist = 4.5
        super.init()
        build()
    }

    required init(from decoder: Decoder) throws {
        self.layer = .somatic
        self.segmentCount = 64
        self.radius = 0.25
        self.height = 1.4
        self.twist = 4.5
        super.init()
        build()
    }

    private func build() {
        for i in 0..<segmentCount {
            let t = Float(i) / Float(max(segmentCount - 1, 1))
            let angle = t * twist * .pi * 2
            let x = cos(angle) * radius
            let z = sin(angle) * radius
            let y = (t - 0.5) * height
            let segment = ModelEntity(mesh: .generateBox(size: SIMD3<Float>(0.02, 0.06, 0.02)))
            segment.position = SIMD3<Float>(x, y, z)
            segment.orientation = simd_quatf(angle: angle, axis: [0, 1, 0])
            segments.append(segment)
            basePositions.append(segment.position)
            addChild(segment)
        }
    }

    func apply(_ state: HelixRibbonState) {
        let pulseScale: Float = 0.9 + 0.3 * state.activity + 0.2 * state.anomaly
        let alpha = CGFloat(min(1, 0.35 + Double(state.activity) * 0.6 + Double(state.uncertainty) * 0.2))
        let base = layer.baseColor
        let color = base.withAlphaComponent(alpha)
        let material = SimpleMaterial(color: color, roughness: 0.2, isMetallic: false)

        for (index, segment) in segments.enumerated() {
            let offset = sin(Float(index) * 0.25) * 0.015 * state.uncertainty
            segment.position = basePositions[index] + SIMD3<Float>(0, offset, 0)
            segment.scale = SIMD3<Float>(repeating: pulseScale)
            segment.model?.materials = [material]
        }
    }
}

/// Marker component used for raycast selection.
@available(visionOS 1.0, *)
public struct SelectableComponent: Component {
    public let selection: H3LIXSelection
    public init(selection: H3LIXSelection) { self.selection = selection }
}

@available(visionOS 1.0, *)
public final class HelixEntity: Entity {
    private let somaticRibbon = RibbonEntity(layer: .somatic)
    private let symbolicRibbon = RibbonEntity(layer: .symbolic, radius: 0.28)
    private let noeticRibbon = RibbonEntity(layer: .noetic, radius: 0.32)
    private let timePlane: ModelEntity

    public required init() {
        let planeMesh = MeshResource.generatePlane(width: 0.9, depth: 0.9)
        let planeMat = SimpleMaterial(color: UIColor.white.withAlphaComponent(0.12), roughness: 0.1, isMetallic: false)
        self.timePlane = ModelEntity(mesh: planeMesh, materials: [planeMat])
        super.init()
        build()
    }

    public required init(from decoder: Decoder) throws {
        let planeMesh = MeshResource.generatePlane(width: 0.9, depth: 0.9)
        let planeMat = SimpleMaterial(color: UIColor.white.withAlphaComponent(0.12), roughness: 0.1, isMetallic: false)
        self.timePlane = ModelEntity(mesh: planeMesh, materials: [planeMat])
        super.init()
        build()
    }

    private func build() {
        addChild(somaticRibbon)
        addChild(symbolicRibbon)
        addChild(noeticRibbon)

        somaticRibbon.components.set(SelectableComponent(selection: .helixLayer(layer: .somatic)))
        symbolicRibbon.components.set(SelectableComponent(selection: .helixLayer(layer: .symbolic)))
        noeticRibbon.components.set(SelectableComponent(selection: .helixLayer(layer: .noetic)))

        timePlane.position = SIMD3<Float>(0, 0, 0)
        addChild(timePlane)
    }

    public func applyVisualState(_ state: HelixVisualState) {
        somaticRibbon.apply(state.somatic)
        symbolicRibbon.apply(state.symbolic)
        noeticRibbon.apply(state.noetic)

        let clamped = max(0, min(1, state.timePlaneHeight))
        timePlane.position.y = (clamped - 0.5) * 1.4
        let alpha = CGFloat(0.2 + 0.4 * state.somatic.anomaly)
        timePlane.model?.materials = [SimpleMaterial(color: UIColor.white.withAlphaComponent(alpha), roughness: 0.1, isMetallic: false)]
    }
}

// MARK: - Body ghost

@available(visionOS 1.0, *)
public final class BodyGhostEntity: Entity {
    struct Sensor {
        let name: String
        let marker: ModelEntity
        let conduit: ModelEntity
    }

    private var sensors: [Sensor] = []
    private let body: ModelEntity

    public required init() {
        let bodyMesh = MeshResource.generateCylinder(height: 1.1, radius: 0.2)
        let bodyMat = SimpleMaterial(color: UIColor.white.withAlphaComponent(0.08), roughness: 0.7, isMetallic: false)
        self.body = ModelEntity(mesh: bodyMesh, materials: [bodyMat])
        super.init()
        build()
    }

    public required init(from decoder: Decoder) throws {
        let bodyMesh = MeshResource.generateCylinder(height: 1.1, radius: 0.2)
        let bodyMat = SimpleMaterial(color: UIColor.white.withAlphaComponent(0.08), roughness: 0.7, isMetallic: false)
        self.body = ModelEntity(mesh: bodyMesh, materials: [bodyMat])
        super.init()
        build()
    }

    private func build() {
        body.position = SIMD3<Float>(0, 0.55, 0.6)
        body.scale = SIMD3<Float>(0.35, 0.35, 0.35)
        addChild(body)

        let sensorPositions: [(String, SIMD3<Float>)] = [
            ("hrv", SIMD3<Float>(0, 0.9, 0.65)),
            ("eda_left", SIMD3<Float>(-0.15, 0.65, 0.65)),
            ("eda_right", SIMD3<Float>(0.15, 0.65, 0.65)),
            ("respiration", SIMD3<Float>(0, 0.75, 0.65)),
            ("gaze", SIMD3<Float>(0, 1.05, 0.55))
        ]

        for (name, position) in sensorPositions {
            let marker = ModelEntity(mesh: .generateSphere(radius: 0.025))
            marker.position = position
            let conduit = ModelEntity(mesh: .generateBox(size: SIMD3<Float>(0.01, 0.4, 0.01)))
            conduit.position = position + SIMD3<Float>(0, 0.2, -0.3)
            conduit.orientation = simd_quatf(angle: -.pi / 5, axis: SIMD3<Float>(1, 0, 0))
            sensors.append(Sensor(name: name, marker: marker, conduit: conduit))
            addChild(marker)
            addChild(conduit)
        }
    }

    public func applySomaticState(_ state: SomaticStatePayload) {
        let features = state.features
        for sensor in sensors {
            let value = features[sensor.name] ?? features.values.average
            let clamped = max(0, min(1, value))
            let color = UIColor.systemTeal.withAlphaComponent(0.4 + CGFloat(clamped) * 0.5)
            let markerMat = SimpleMaterial(color: color, roughness: 0.3, isMetallic: false)
            sensor.marker.model?.materials = [markerMat]

            let conduitColor = UIColor.systemTeal.withAlphaComponent(0.2 + CGFloat(state.changePoint ? 0.5 : clamped) * 0.6)
            let conduitMat = SimpleMaterial(color: conduitColor, roughness: 0.2, isMetallic: false)
            sensor.conduit.model?.materials = [conduitMat]
            let pulse = state.changePoint ? 1.15 : 1 + Float(clamped) * 0.1
            sensor.marker.setScale(SIMD3<Float>(repeating: pulse), relativeTo: nil)
        }
    }
}

// MARK: - Halo

@available(visionOS 1.0, *)
public final class NoeticHaloEntity: Entity {
    private let surfaceEntity: ModelEntity
    private var bandEntities: [ModelEntity] = []

    public required init() {
        let surfaceMesh = MeshResource.generateSphere(radius: 0.5)
        let surfaceMat = UnlitMaterial(color: UIColor.systemTeal.withAlphaComponent(0.08))
        surfaceEntity = ModelEntity(mesh: surfaceMesh, materials: [surfaceMat])
        super.init()
        buildBands()
        addChild(surfaceEntity)
    }

    public required init(from decoder: Decoder) throws {
        let surfaceMesh = MeshResource.generateSphere(radius: 0.5)
        let surfaceMat = UnlitMaterial(color: UIColor.systemTeal.withAlphaComponent(0.08))
        surfaceEntity = ModelEntity(mesh: surfaceMesh, materials: [surfaceMat])
        super.init()
        buildBands()
        addChild(surfaceEntity)
    }

    private func buildBands() {
        let bandCount = 4
        for i in 0..<bandCount {
            let radius = 0.55 + Float(i) * 0.05
            // Torus mesh not available on all platforms; use a thin sphere shell as a fallback ring proxy.
            let mesh: MeshResource? = nil
            let mat = UnlitMaterial(color: UIColor.systemTeal.withAlphaComponent(0.06))
            let band = ModelEntity(mesh: mesh ?? .generateSphere(radius: radius), materials: [mat])
            band.position.y = Float(i) * 0.05
            bandEntities.append(band)
            addChild(band)
        }
    }

    public func applyVisualState(_ state: HaloVisualState) {
        let baseAlpha = CGFloat(0.05 + Double(state.globalCoherence) * 0.18)
        surfaceEntity.model?.materials = [
            UnlitMaterial(color: UIColor.systemTeal.withAlphaComponent(baseAlpha))
        ]
        surfaceEntity.scale = SIMD3<Float>(repeating: 0.6 + 0.04 * state.pulse)

        for (idx, band) in bandEntities.enumerated() {
            guard idx < state.bands.count else { continue }
            let bandState = state.bands[idx]
            let alpha = CGFloat(0.04 + Double(bandState.intensity) * 0.2)
            band.model?.materials = [
                UnlitMaterial(
                    color: UIColor.systemTeal.withAlphaComponent(alpha)
                )
            ]
        }
    }
}

// MARK: - MPG city

@available(visionOS 1.0, *)
public final class MpgCityEntity: Entity {
    private var nodeEntities: [String: ModelEntity] = [:]
    private var edgeEntities: [String: ModelEntity] = [:]
    private var rogueHalos: [String: ModelEntity] = [:]
    private let maxVisibleNodes = 800

    public required init() {
        super.init()
    }

    public required init(from decoder: Decoder) throws {
        super.init()
    }

    public func applyVisualState(_ visual: MpgVisualState, rogue: RogueOverlayState?, mufs: MufsOverlayState?) {
        let visibleNodes = Array(visual.nodes.prefix(maxVisibleNodes))
        var seenNodes: Set<String> = []

        for node in visibleNodes {
            seenNodes.insert(node.id)
            if let existing = nodeEntities[node.id] {
                updateNode(existing, with: node)
            } else {
                let entity = createNode(with: node)
                nodeEntities[node.id] = entity
                addChild(entity)
            }

            if node.isRogueHotspot {
                attachRogueHalo(to: node)
            } else {
                removeRogueHalo(for: node.id)
            }
        }

        for (id, entity) in nodeEntities where !seenNodes.contains(id) {
            entity.removeFromParent()
            nodeEntities[id] = nil
            removeRogueHalo(for: id)
        }

        var seenEdges: Set<String> = []
        for edge in visual.edges {
            guard edge.fromIndex < visibleNodes.count, edge.toIndex < visibleNodes.count else { continue }
            let fromNode = visibleNodes[edge.fromIndex]
            let toNode = visibleNodes[edge.toIndex]
            guard let start = nodeEntities[fromNode.id]?.position(relativeTo: parent),
                  let end = nodeEntities[toNode.id]?.position(relativeTo: parent) else { continue }
            seenEdges.insert(edge.id)
            if let existing = edgeEntities[edge.id] {
                updateEdge(existing, start: start, end: end, edge: edge)
            } else {
                let e = createEdge(start: start, end: end, edge: edge)
                edgeEntities[edge.id] = e
                addChild(e)
            }
        }

        for (id, entity) in edgeEntities where !seenEdges.contains(id) {
            entity.removeFromParent()
            edgeEntities[id] = nil
        }

        // Basic LOD indicator: downsample edges if exceeding budget.
        let reduceEdges = visual.edges.count > maxVisibleNodes * 2
        var toggle = false
        for (_, entity) in edgeEntities {
            if reduceEdges {
                toggle.toggle()
                entity.isEnabled = toggle
            } else {
                entity.isEnabled = true
            }
        }
    }

    private func createNode(with node: MpgNodeInstance) -> ModelEntity {
        let mesh = MeshResource.generateSphere(radius: 0.08)
        let material = nodeMaterial(for: node)
        let entity = ModelEntity(mesh: mesh, materials: [material])
        updateNode(entity, with: node)
        entity.components.set(SelectableComponent(selection: .mpgNode(nodeId: node.id)))
        return entity
    }

    private func updateNode(_ entity: ModelEntity, with node: MpgNodeInstance) {
        entity.position = node.position
        let width = max(0.12, 0.12 + 0.12 * node.stability)
        let height = max(0.14, 0.14 + 0.24 * node.importance)
        entity.scale = SIMD3<Float>(width, height, width)
        entity.model?.materials = [nodeMaterial(for: node)]
    }

    private func nodeMaterial(for node: MpgNodeInstance) -> UnlitMaterial {
        let hue: CGFloat = node.valence >= 0 ? 0.1 + CGFloat(node.valence) * 0.12 : 0.55 + CGFloat(abs(node.valence)) * 0.1
        let saturation: CGFloat = 0.65 + CGFloat(node.importance) * 0.2
        let brightness: CGFloat = 0.7 + CGFloat(node.confidence) * 0.25
        var color = UIColor(hue: hue, saturation: saturation, brightness: brightness, alpha: 0.9)
        if node.isMufsElement {
            color = color.withAlphaComponent(0.5)
        }
        if node.isRogueHotspot {
            color = UIColor(red: 1.0, green: 0.42, blue: 0.3, alpha: 1.0)
        }
        return UnlitMaterial(color: color)
    }

    private func createEdge(start: SIMD3<Float>, end: SIMD3<Float>, edge: MpgEdgeInstance) -> ModelEntity {
        let delta = end - start
        let length = simd_length(delta)
        let mesh = MeshResource.generateBox(size: SIMD3<Float>(0.005 + 0.01 * edge.strength, length, 0.005))
        let material = edgeMaterial(for: edge)
        let entity = ModelEntity(mesh: mesh, materials: [material])
        entity.position = (start + end) / 2
        if length > 0.0001 {
            entity.orientation = simd_quatf(from: SIMD3<Float>(0, 1, 0), to: simd_normalize(delta))
        }
        return entity
    }

    private func updateEdge(_ entity: ModelEntity, start: SIMD3<Float>, end: SIMD3<Float>, edge: MpgEdgeInstance) {
        let delta = end - start
        let length = simd_length(delta)
        entity.position = (start + end) / 2
        if length > 0.0001 {
            entity.orientation = simd_quatf(from: SIMD3<Float>(0, 1, 0), to: simd_normalize(delta))
            entity.model?.mesh = MeshResource.generateBox(size: SIMD3<Float>(0.005 + 0.01 * edge.strength, length, 0.005))
        }
        entity.model?.materials = [edgeMaterial(for: edge)]
    }

    private func edgeMaterial(for edge: MpgEdgeInstance) -> UnlitMaterial {
        let colors: [UIColor] = [
            UIColor(red: 0.1, green: 0.8, blue: 0.9, alpha: 1),
            UIColor(red: 0.95, green: 0.45, blue: 0.25, alpha: 1),
            UIColor(red: 0.6, green: 0.55, blue: 1.0, alpha: 1),
            UIColor(red: 0.2, green: 0.95, blue: 0.5, alpha: 1),
            UIColor(red: 0.95, green: 0.8, blue: 0.25, alpha: 1),
            UIColor(red: 0.4, green: 0.9, blue: 0.8, alpha: 1)
        ]
        let base = colors[edge.typeIndex % colors.count]
        let alpha = 0.25 + CGFloat(edge.strength) * 0.45
        return UnlitMaterial(color: base.withAlphaComponent(alpha))
    }

    private func attachRogueHalo(to node: MpgNodeInstance) {
        if rogueHalos[node.id] != nil { return }
        let ring = ModelEntity(mesh: MeshResource.generateSphere(radius: 0.15))
        ring.model?.materials = [SimpleMaterial(color: UIColor.red.withAlphaComponent(0.6), roughness: 0.2, isMetallic: false)]
        ring.position = node.position + SIMD3<Float>(0, 0.25, 0)
        rogueHalos[node.id] = ring
        addChild(ring)
    }

    private func removeRogueHalo(for nodeID: String) {
        if let ring = rogueHalos[nodeID] {
            ring.removeFromParent()
            rogueHalos[nodeID] = nil
        }
    }
}

// MARK: - SORK ring

@available(visionOS 1.0, *)
public final class SorkRingEntity: Entity {
    private let ringModel: ModelEntity
    private var phaseMarkers: [ModelEntity] = []
    private let comet: ModelEntity

    public required init() {
        ringModel = ModelEntity(mesh: MeshResource.generateSphere(radius: 0.6))
        comet = ModelEntity(mesh: MeshResource.generateSphere(radius: 0.03))
        super.init()
        build()
    }

    public required init(from decoder: Decoder) throws {
        ringModel = ModelEntity(mesh: MeshResource.generateSphere(radius: 0.6))
        comet = ModelEntity(mesh: MeshResource.generateSphere(radius: 0.03))
        super.init()
        build()
    }

    private func build() {
        ringModel.model?.materials = [SimpleMaterial(color: UIColor.systemIndigo.withAlphaComponent(0.35), roughness: 0.4, isMetallic: false)]
        ringModel.position = SIMD3<Float>(0, 0.4, 0)
        addChild(ringModel)

        let labels = ["S", "O", "R", "K", "N", "S′"]
        for i in 0..<labels.count {
            let angle = Float(i) / Float(labels.count) * 2 * .pi
            let pos = SIMD3<Float>(cos(angle) * 0.6, 0.4, sin(angle) * 0.6)
            let marker = ModelEntity(mesh: MeshResource.generateSphere(radius: 0.02))
            marker.position = pos
            marker.model?.materials = [SimpleMaterial(color: UIColor.systemIndigo.withAlphaComponent(0.4), roughness: 0.4, isMetallic: false)]
            marker.components.set(SelectableComponent(selection: .sorkPhase(phase: phaseForIndex(i))))
            phaseMarkers.append(marker)
            addChild(marker)
        }

        comet.model?.materials = [SimpleMaterial(color: UIColor.systemOrange.withAlphaComponent(0.8), roughness: 0.2, isMetallic: false)]
        comet.position = SIMD3<Float>(0.6, 0.4, 0)
        addChild(comet)
    }

    public func applyVisualState(_ state: SorkVisualState) {
        let count = max(phaseMarkers.count, 1)
        for (idx, marker) in phaseMarkers.enumerated() {
            guard idx < state.phases.count else { continue }
            let phase = state.phases[idx]
            let baseColor = phase.active ? UIColor.systemOrange : UIColor.systemIndigo
            let alpha = phase.active ? 0.8 : 0.35
            marker.model?.materials = [SimpleMaterial(color: baseColor.withAlphaComponent(alpha), roughness: 0.3, isMetallic: false)]
        }

        let angle = state.cometAngle
        comet.position = SIMD3<Float>(cos(angle) * 0.6, 0.4, sin(angle) * 0.6)
    }

    private func phaseForIndex(_ index: Int) -> SorkPhase {
        let phases: [SorkPhase] = [.S, .O, .R, .K, .N, .SPrime]
        return phases[index % phases.count]
    }
}

// MARK: - Coordinator

@available(visionOS 1.0, *)
@MainActor
public final class H3LIXSceneCoordinator {
    private let store: H3LIXStore
    private let builder = VisualStateBuilder()
    private let playback: H3LIXPlaybackController
    private let interaction: H3LIXInteractionModel
    private let wall = CoherenceWallEntity()
    private weak var helix: HelixEntity?
    private weak var body: BodyGhostEntity?
    private weak var city: MpgCityEntity?
    private weak var halo: NoeticHaloEntity?
    private weak var sork: SorkRingEntity?
    private var cancellables: Set<AnyCancellable> = []
    private var snapshotLogCounter = 0

    public init(store: H3LIXStore, playback: H3LIXPlaybackController, interaction: H3LIXInteractionModel) {
        self.store = store
        self.playback = playback
        self.interaction = interaction
        bindStore()
        builder.start()
        print("[H3LIX] SceneCoordinator init")
    }

    public func bind(helix: HelixEntity, body: BodyGhostEntity, city: MpgCityEntity, halo: NoeticHaloEntity, sork: SorkRingEntity) {
        self.helix = helix
        self.body = body
        self.city = city
        self.halo = halo
        self.sork = sork
        // Position wall in the background; root setup occurs in immersive view.
        helix.parent?.addChild(wall)
        wall.position = SIMD3<Float>(0, 1.2, -1.5)

        builder.$snapshot
            .removeDuplicates() // VisualSnapshot is Equatable
            .sink { [weak self] snapshot in
                guard let self else { return }
                snapshotLogCounter += 1
                if snapshotLogCounter % 10 == 0 {
                    print("[H3LIX] SceneCoordinator apply snapshot visuals helix=\(snapshot.helix.timePlaneHeight) nodes=\(snapshot.mpg.nodes.count) edges=\(snapshot.mpg.edges.count)")
                }
                self.helix?.applyVisualState(snapshot.helix)
                self.halo?.applyVisualState(snapshot.halo)
                self.city?.applyVisualState(snapshot.mpg, rogue: snapshot.rogue, mufs: snapshot.mufs)
                self.sork?.applyVisualState(snapshot.sork)
                self.wall.apply(snapshot.wall)
            }
            .store(in: &cancellables)

        store.$somatic
            .compactMap { $0 }
            .sink { [weak self] somatic in
                self?.body?.applySomaticState(somatic)
            }
            .store(in: &cancellables)
    }

    private func bindStore() {
        store.$somatic
            .compactMap { $0 }
            .sink { [weak builder] payload in builder?.ingest(somatic: payload) }
            .store(in: &cancellables)

        store.$symbolic
            .compactMap { $0 }
            .sink { [weak builder] payload in builder?.ingest(symbolic: payload) }
            .store(in: &cancellables)

        store.$noetic
            .compactMap { $0 }
            .sink { [weak builder] payload in builder?.ingest(noetic: payload) }
            .store(in: &cancellables)

        store.$decisionCycle
            .compactMap { $0 }
            .sink { [weak builder] payload in builder?.ingest(decision: payload) }
            .store(in: &cancellables)

        store.$mpg
            .sink { [weak builder] graph in builder?.ingest(graph: graph) }
            .store(in: &cancellables)

        store.$rogueEvents
            .compactMap { $0.first }
            .sink { [weak builder] rogue in builder?.ingest(rogue: rogue) }
            .store(in: &cancellables)

        store.$mufsEvents
            .compactMap { $0.first }
            .sink { [weak builder] mufs in builder?.ingest(mufs: mufs) }
            .store(in: &cancellables)

        store.$cohortSummary
            .sink { [weak builder, weak store] summary in
                builder?.setCohortSummary(summary: summary, echoes: store?.cohortEchoes)
            }
            .store(in: &cancellables)

        store.$cohortEchoes
            .sink { [weak builder, weak store] echoes in
                builder?.setCohortSummary(summary: store?.cohortSummary, echoes: echoes)
            }
            .store(in: &cancellables)

        interaction.$mode
            .sink { [weak self] mode in
                guard let self else { return }
                switch mode {
                case .live, .replay:
                    self.builder.setRogueOverride(segmentIds: nil)
                    self.builder.setMufsOverride(nodeIds: nil)
                case .rogueInspect(let rogueId):
                    if let event = self.store.rogueEvents.first(where: { $0.rogueID == rogueId }) {
                        self.builder.setRogueOverride(segmentIds: event.segmentIDs)
                    }
                case .mufsInspect(let decisionId):
                    if let event = self.store.mufsEvents.first(where: { $0.decisionID == decisionId }) {
                        self.builder.setMufsOverride(nodeIds: event.processUnawareNodeIds)
                    }
                }
            }
            .store(in: &cancellables)

        interaction.$wallVisible
            .sink { [weak self] visible in
                self?.wall.isEnabled = visible
            }
            .store(in: &cancellables)

        playback.$tRelMs
            .sink { [weak builder] t in
                builder?.setTimeOverride(tRelMs: t)
            }
            .store(in: &cancellables)

        playback.$mode
            .sink { [weak builder] mode in
                if case .live = mode {
                    builder?.setTimeOverride(tRelMs: nil)
                }
            }
            .store(in: &cancellables)

        store.$latestTRelMs
            .sink { [weak playback] t in
                playback?.setLiveTime(t)
            }
            .store(in: &cancellables)

        playback.onReplayEnvelopes = { [weak self] envelopes in
            envelopes.forEach { envelope in
                self?.store.apply(envelope: envelope)
            }
        }
    }
}

// MARK: - Helpers

private extension Collection where Element == Double {
    var average: Double {
        guard !isEmpty else { return 0 }
        return reduce(0, +) / Double(count)
    }
}
