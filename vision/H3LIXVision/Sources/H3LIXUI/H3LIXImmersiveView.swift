#if os(visionOS)
import SwiftUI
import RealityKit
import H3LIXScene
import H3LIXState

public struct H3LIXImmersiveView: View {
    private static let registerSelectableComponent: Void = {
        // RealityKit needs explicit registration for custom components used in gestures.
        SelectableComponent.registerComponent()
    }()

    @ObservedObject private var store: H3LIXStore
    @ObservedObject private var playback: H3LIXPlaybackController
    @ObservedObject private var interaction: H3LIXInteractionModel
    @ObservedObject private var teaching: TeachingStore
    @State private var coordinator: H3LIXSceneCoordinator?
    @State private var realityInitialized = false
    @State private var debugMessage = "Not started"
    @State private var sceneScale: Float = 0.8
    @State private var sceneDepth: Float = -0.9
    @State private var sceneHeight: Float = -0.15

    public init(store: H3LIXStore, playback: H3LIXPlaybackController, interaction: H3LIXInteractionModel, teaching: TeachingStore) {
        print("[H3LIX] H3LIXImmersiveView init")
        _ = Self.registerSelectableComponent
        self.store = store
        self.playback = playback
        self.interaction = interaction
        self.teaching = teaching
    }

    public var body: some View {
        print("[H3LIX] H3LIXImmersiveView body constructed")
        return ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.05, green: 0.07, blue: 0.11),
                    Color(red: 0.01, green: 0.03, blue: 0.06)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            RealityView { content in
                realityInitialized = true
                debugMessage = "RealityView init"
                print("[H3LIX] RealityView closure executing")
                // World-anchored scene so the user can move/zoom relative to content.
                let sceneRoot = AnchorEntity(world: SIMD3<Float>(0, sceneHeight, sceneDepth))
                sceneRoot.name = "sceneRoot"
                sceneRoot.scale = SIMD3<Float>(repeating: sceneScale)

                let rig = Entity()
                rig.position = .zero
                rig.scale = SIMD3<Float>(repeating: 0.5) // modest scale so scene sits comfortably
                sceneRoot.addChild(rig)

            // Simple sky
            let sky = ModelEntity(
                mesh: .generateSphere(radius: 8.0),
                materials: [UnlitMaterial(color: .init(red: 0.03, green: 0.05, blue: 0.09, alpha: 1))]
            )
            sky.scale = SIMD3<Float>(-1, 1, 1)
            sceneRoot.addChild(sky)

            // Lights
            let keyLight = DirectionalLight()
            keyLight.light.intensity = 1_400
            keyLight.light.color = .white.withAlphaComponent(0.9)
            keyLight.orientation = simd_quatf(angle: -.pi / 3, axis: SIMD3<Float>(1, 0.1, 0.1))
            rig.addChild(keyLight)

            let fillLight = DirectionalLight()
            fillLight.light.intensity = 600
            fillLight.light.color = .white.withAlphaComponent(0.7)
            fillLight.orientation = simd_quatf(angle: .pi / 5, axis: SIMD3<Float>(-1, 0, 0))
            rig.addChild(fillLight)

            let rimLight = DirectionalLight()
            rimLight.light.intensity = 400
            rimLight.light.color = .white.withAlphaComponent(0.6)
            rimLight.orientation = simd_quatf(angle: .pi, axis: SIMD3<Float>(0, 1, 0))
            rig.addChild(rimLight)

            // Floor / marker
            let floor = ModelEntity(
                mesh: .generatePlane(width: 4.0, depth: 4.0),
                materials: [UnlitMaterial(color: .init(white: 0.07, alpha: 0.85))]
            )
            floor.position = SIMD3<Float>(0, -0.12, 0)
            rig.addChild(floor)

            let helix = HelixEntity()
            let body = BodyGhostEntity()
            let city = MpgCityEntity()
            let halo = NoeticHaloEntity()
            let sork = SorkRingEntity()

            helix.position = SIMD3<Float>(0, 0.18, 0)
            city.position = SIMD3<Float>(0, 0.02, 0)
            halo.position = SIMD3<Float>(0, 0.1, 0)
            sork.position = SIMD3<Float>(0, 0.05, 0)

            [helix, body, city, halo, sork].forEach { entity in
                entity.scale = SIMD3<Float>(repeating: 0.6)
                rig.addChild(entity)
            }

            content.add(sceneRoot)
            print("[H3LIX] RealityView initialized sceneRoot scale=\(sceneScale) pos=(0,\(sceneHeight),\(sceneDepth)) snapshotNodes=\(store.snapshot?.mpg.baseSubgraph.nodes.count ?? 0)")
            debugMessage = "Scene root added, snapshot nodes=\(store.snapshot?.mpg.baseSubgraph.nodes.count ?? 0)"

            if coordinator == nil {
                let newCoordinator = H3LIXSceneCoordinator(store: store, playback: playback, interaction: interaction)
                newCoordinator.bind(helix: helix, body: body, city: city, halo: halo, sork: sork)
                coordinator = newCoordinator
            }
        } update: { content in
            if let sceneRoot = content.entities.first(where: { $0.name == "sceneRoot" }) {
                sceneRoot.position = SIMD3<Float>(0, sceneHeight, sceneDepth)
                sceneRoot.scale = SIMD3<Float>(repeating: sceneScale)
            }
        }
            .gesture(
                SpatialTapGesture()
                    .targetedToAnyEntity()
                    .onEnded { value in
                    if let selectable = value.entity.components[SelectableComponent.self] {
                        interaction.select(selectable.selection)
                    }
                }
        )
        .overlay(alignment: .topTrailing) {
            SelectionHUDView(store: store, interaction: interaction)
                .padding()
        }
        .overlay(alignment: .topLeading) {
            VStack(alignment: .leading, spacing: 6) {
                if let snap = store.snapshot {
                    Text("Snapshot: \(snap.sessionID)")
                        .font(.caption.weight(.semibold))
                    Text("t=\(snap.tRelMs) ms · nodes \(snap.mpg.baseSubgraph.nodes.count)")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                } else {
                    Text("No snapshot loaded")
                        .font(.caption.weight(.semibold))
                    Text("Pick a scenario or load a snapshot before entering immersive.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if case .error(let msg) = store.connectionState {
                    Text("Error: \(msg)")
                        .font(.caption2)
                        .foregroundStyle(.red)
                }
            }
            .padding(10)
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            .padding()
        }
        .overlay(alignment: .bottomTrailing) {
            if let step = teaching.currentStep {
                TeachingOverlay(step: step, onPrev: { teaching.previousStep() }, onNext: { teaching.nextStep() })
                    .padding()
            }
        }
        // Center debug panel to guarantee something is visible even if 3D content fails.
        .overlay {
            VStack(spacing: 8) {
                Text("H3LIX Immersive")
                    .font(.title3.weight(.bold))
                    .foregroundStyle(.white)
                Text(debugMessage)
                    .font(.caption.monospaced())
                    .foregroundStyle(.white.opacity(0.8))
                if let snap = store.snapshot {
                    Text("Snapshot \(snap.sessionID) t=\(snap.tRelMs) nodes=\(snap.mpg.baseSubgraph.nodes.count)")
                        .font(.caption2.monospaced())
                        .foregroundStyle(.white.opacity(0.7))
                } else {
                    Text("No snapshot loaded")
                        .font(.caption2)
                        .foregroundStyle(.white.opacity(0.7))
                }
            }
            .padding(12)
            .background(Color.black.opacity(0.6))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        // Simple positioning controls for simulator: zoom and depth adjust.
        .overlay(alignment: .bottom) {
            HStack(spacing: 12) {
                Button {
                    sceneScale = max(0.2, sceneScale - 0.05)
                } label: {
                    Label("Zoom -", systemImage: "minus.magnifyingglass")
                }
                .buttonStyle(.bordered)

                Slider(value: Binding(get: {
                    Double(sceneScale)
                }, set: { newValue in
                    sceneScale = Float(newValue)
                }), in: 0.2...1.2)
                .frame(width: 200)

                Button {
                    sceneScale = min(1.2, sceneScale + 0.05)
                } label: {
                    Label("Zoom +", systemImage: "plus.magnifyingglass")
                }
                .buttonStyle(.bordered)

                Button {
                    sceneDepth += 0.1
                } label: {
                    Label("Closer", systemImage: "arrow.up.to.line.compact")
                }
                .buttonStyle(.bordered)

                Button {
                    sceneDepth -= 0.1
                } label: {
                    Label("Farther", systemImage: "arrow.down.to.line.compact")
                }
                .buttonStyle(.bordered)

                Button {
                    sceneHeight += 0.05
                } label: {
                    Label("Up", systemImage: "arrow.up")
                }
                .buttonStyle(.bordered)

                Button {
                    sceneHeight -= 0.05
                } label: {
                    Label("Down", systemImage: "arrow.down")
                }
                .buttonStyle(.bordered)

                Button("Reset") {
                    sceneScale = 0.8
                    sceneDepth = -0.9
                    sceneHeight = -0.15
                }
                .buttonStyle(.bordered)
            }
            .padding()
            .background(Color.black.opacity(0.35))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .padding(.bottom, 24)
        }
            // Simple always-on HUD to verify immersive rendering in simulator.
            VStack {
                Text("Immersive view active \(realityInitialized ? "✅" : "…")")
                    .font(.headline)
                    .foregroundStyle(.white)
                    .padding(8)
                    .background(Color.black.opacity(0.4))
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                Spacer()
            }
            .padding()
            .onAppear {
                print("[H3LIX] Immersive SwiftUI overlay appeared realityInitialized=\(realityInitialized)")
            }
            .background(Color.black.opacity(0.01)) // ensures view tree stays active
        }
    }
}
#endif
