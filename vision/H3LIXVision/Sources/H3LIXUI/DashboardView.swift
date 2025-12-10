#if os(visionOS)
import SwiftUI
import H3LIXState
import H3LIXCore

public struct DashboardView: View {
    @ObservedObject private var store: H3LIXStore
    @ObservedObject private var playback: H3LIXPlaybackController
    @ObservedObject private var interaction: H3LIXInteractionModel
    @ObservedObject private var teaching: TeachingStore
    @Binding private var immersiveSpaceIsShown: Bool
    private let immersiveSpaceID: String
    @State private var selectedSessionID: String?
    @State private var selectedScenarioID: String?
    @State private var selectedCohortID: String?
    @State private var isOpeningImmersive = false
    @State private var showErrorDetails = false
    @State private var lastErrorMessage: String?
    @State private var immersiveStatus: String?
    @State private var autoImmersiveAttempted = false
    @Environment(\.openImmersiveSpace) private var openImmersiveSpace
    @Environment(\.dismissImmersiveSpace) private var dismissImmersiveSpace

    public init(store: H3LIXStore, playback: H3LIXPlaybackController, interaction: H3LIXInteractionModel, teaching: TeachingStore, immersiveSpaceIsShown: Binding<Bool>, immersiveSpaceID: String = "ImmersiveSpace") {
        self.store = store
        self.playback = playback
        self.interaction = interaction
        self.teaching = teaching
        self._immersiveSpaceIsShown = immersiveSpaceIsShown
        self.immersiveSpaceID = immersiveSpaceID
    }

    public var body: some View {
        mainContent
    }

    @ViewBuilder
    private var mainContent: some View {
        ScrollView(.vertical) {
            VStack(alignment: .leading, spacing: 16) {
                header
                scenarioPanel
                sessionPicker
                controls
                cohortSection
                timeline
                Divider()
                telemetrySummary
                symbiosisPanel
                eventHud
                teachingSection
            }
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .scrollIndicators(.hidden)
        .tint(.blue)
        .onChange(of: immersiveSpaceIsShown) { newValue in
            print("[H3LIX] immersiveSpaceIsShown changed -> \(newValue)")
        }
        .onAppear {
            if store.sessions.isEmpty {
                store.refreshSessions()
            }
            if store.cohorts.isEmpty {
                store.refreshCohorts()
            }
            if teaching.lessons.isEmpty {
                teaching.refreshLessons()
            }
            if selectedSessionID == nil {
                selectedSessionID = store.sessions.first?.id
            }
            if selectedCohortID == nil {
                selectedCohortID = store.cohorts.first?.id
            }
            if selectedScenarioID == nil {
                selectedScenarioID = store.scenarioPresets.first?.id
            }
            if !autoImmersiveAttempted && !immersiveSpaceIsShown {
                autoImmersiveAttempted = true
                print("[H3LIX] Dashboard appeared; auto-enter immersive attempt (showing=\(immersiveSpaceIsShown))")
                immersiveStatus = "Auto requesting immersive open..."
                Task {
                    await toggleImmersiveSpace()
                }
            }
        }
        .onChange(of: store.sessions) { sessions in
            if selectedSessionID == nil {
                selectedSessionID = sessions.first?.id
            }
        }
        .onChange(of: store.cohorts) { cohorts in
            if selectedCohortID == nil {
                selectedCohortID = cohorts.first?.id
            }
        }
        .alert("Stream Error", isPresented: $showErrorDetails) {
            Button("Dismiss", role: .cancel) { }
            Button("Restart Stream") {
                if let id = selectedSessionID {
                    store.startStream(sessionID: id)
                }
            }
        } message: {
            if case .error(let message) = store.connectionState {
                Text(message)
            } else if let lastErrorMessage {
                Text(lastErrorMessage)
            } else {
                Text("Unknown error")
            }
        }
    }

    private func avg(_ values: [Double]) -> Double {
        guard !values.isEmpty else { return 0 }
        return values.reduce(0, +) / Double(values.count)
    }

    private func fmt(_ value: Double) -> String {
        value.formatted(.number.precision(.fractionLength(2)))
    }

    private var teachingSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Guided Lessons")
                .font(.headline)
            if let lesson = teaching.activeLesson, let step = teaching.currentStep {
                VStack(alignment: .leading, spacing: 4) {
                    Text(lesson.title).font(.subheadline)
                    Text(step.title).font(.caption).foregroundStyle(.secondary)
                }
                HStack(spacing: 8) {
                    Button("Prev") { teaching.previousStep() }.buttonStyle(.bordered)
                    Button("Next") { teaching.nextStep() }.buttonStyle(.borderedProminent)
                }
            } else {
                Text("No lesson loaded").font(.caption).foregroundStyle(.secondary)
                Button("Load Lessons") { teaching.refreshLessons() }.buttonStyle(.bordered)
            }
        }
        .padding()
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("H3LIX Vision")
                .font(.largeTitle.weight(.bold))
            Text("Select a session, load a snapshot, and step into the immersive brain space.")
                .foregroundStyle(.secondary)
                .font(.callout)
            Text("Quick start: pick a scenario below, then Load Snapshot and Enter Immersive Space.")
                .foregroundStyle(.secondary)
                .font(.caption)
        }
    }

    private var scenarioPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Scenario Switcher")
                    .font(.headline)
                Spacer()
                if let selectedScenarioID,
                   let active = store.scenarioPresets.first(where: { $0.id == selectedScenarioID }) {
                    Button("Apply \(active.title)") {
                        loadScenario(active)
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
            Text("Use scenarios to instantly repopulate the world without wiring up a backend.")
                .font(.caption)
                .foregroundStyle(.secondary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(store.scenarioPresets) { scenario in
                        scenarioCard(for: scenario)
                    }
                }
            }
            .scrollIndicators(.hidden)
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func scenarioCard(for scenario: ScenarioPreset) -> some View {
        let isSelected = selectedScenarioID == scenario.id
        return Button {
            selectedScenarioID = scenario.id
            loadScenario(scenario)
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                Text(scenario.title).font(.subheadline.weight(.semibold))
                Text(scenario.subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                HStack(spacing: 8) {
                    if scenario.rogue != nil {
                        Label("Rogue", systemImage: "flame.fill")
                            .font(.caption2)
                            .foregroundStyle(.orange)
                    }
                    if scenario.mufs != nil {
                        Label("MUFS", systemImage: "exclamationmark.shield.fill")
                            .font(.caption2)
                            .foregroundStyle(.blue)
                    }
                }
            }
            .padding(12)
            .frame(width: 230, height: 130, alignment: .leading)
            .background(isSelected ? Color.accentColor.opacity(0.2) : Color.white.opacity(0.05))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(isSelected ? Color.accentColor : Color.primary.opacity(0.08), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private func loadScenario(_ scenario: ScenarioPreset) {
        store.applyScenario(scenario)
        playback.resumeLive()
        playback.setLiveTime(scenario.snapshot.tRelMs)
        interaction.setMode(.live)
    }

    private var sessionPicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Sessions")
                    .font(.headline)
                Spacer()
                Button("Refresh") {
                    store.refreshSessions()
                }
                .buttonStyle(.bordered)
            }

            ScrollView(.vertical) {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(store.sessions) { session in
                        Button {
                            selectedSessionID = session.id
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(session.id).font(.headline)
                                    Text("\(session.experimentID) · \(session.subjectID)")
                                        .foregroundStyle(.secondary)
                                        .font(.caption)
                                }
                                Spacer()
                                Text(session.status)
                                    .font(.caption)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(.thinMaterial)
                                    .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(selectedSessionID == session.id ? Color.accentColor.opacity(0.15) : Color.clear)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .frame(height: 200)
        }
    }

    private var controls: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Controls")
                .font(.headline)
            HStack(spacing: 12) {
                Button("Load Snapshot") {
                    if let id = selectedSessionID {
                        store.loadSnapshot(for: id)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(selectedSessionID == nil)

                let streaming = {
                    if case .streaming = store.connectionState { return true }
                    return false
                }()

                Button(streaming ? "Restart Stream" : "Start Stream") {
                    if let id = selectedSessionID {
                        store.startStream(sessionID: id)
                    }
                }
                .buttonStyle(.bordered)
                .disabled(selectedSessionID == nil)

                Button("Stop Stream") {
                    store.stopStream()
                }
                .buttonStyle(.bordered)
                .disabled(!streaming)

                VStack(alignment: .leading, spacing: 4) {
                    Button(immersiveSpaceIsShown ? "Hide Immersive Space" : "Enter Immersive Space") {
                        Task {
                            print("[H3LIX] Immersive button tapped showing=\(immersiveSpaceIsShown)")
                            immersiveStatus = immersiveSpaceIsShown ? "Hiding immersive..." : "Opening immersive..."
                            await toggleImmersiveSpace()
                        }
                    }
                    .buttonStyle(.bordered)
                    .disabled(isOpeningImmersive)

                    Button("Force Hide") {
                        Task {
                            print("[H3LIX] Force hide immersive requested")
                            await dismissImmersiveSpace()
                            immersiveSpaceIsShown = false
                            immersiveStatus = "Force dismissed"
                        }
                    }
                    .buttonStyle(.borderless)
                    .font(.caption)

                    if let immersiveStatus {
                        Text("Immersive: \(immersiveStatus)")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.leading, 8)

                Toggle("Show Coherence Wall", isOn: Binding(get: {
                    interaction.wallVisible
                }, set: { interaction.wallVisible = $0 }))
                .toggleStyle(.switch)
            }
            connectionBanner
            modeBanner
        }
    }

    private var connectionBanner: some View {
        HStack {
            switch store.connectionState {
            case .idle:
                Label("Idle", systemImage: "pause.fill").foregroundStyle(.secondary)
            case .loadingSnapshot(let sessionID):
                Label("Loading snapshot \(sessionID)", systemImage: "arrow.down.to.line.compact").foregroundStyle(.blue)
            case .streaming(let sessionID):
                Label("Streaming \(sessionID)", systemImage: "waveform").foregroundStyle(.green)
            case .error(let message):
                Label(message, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                    .onTapGesture { showErrorDetails.toggle() }
            }
            Spacer()
        }
        .font(.caption)
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    private var modeBanner: some View {
        HStack(spacing: 12) {
            Text("Mode: \(modeLabel)")
                .font(.caption)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(.thinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            Button("Return to Live") {
                interaction.setMode(.live)
                playback.resumeLive()
            }
            .buttonStyle(.bordered)
        }
    }

    private var telemetrySummary: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Live Telemetry")
                .font(.headline)
            HStack(spacing: 12) {
                summaryTile(
                    title: "Somatic",
                    value: avg(store.somatic.map { Array($0.features.values) } ?? []),
                    footer: store.somatic?.changePoint == true ? "Change-point" : "Stable"
                )
                summaryTile(
                    title: "Symbolic",
                    value: avg(store.symbolic?.beliefs.map(\.confidence) ?? []),
                    footer: "\(store.symbolic?.beliefs.count ?? 0) beliefs"
                )
                summaryTile(
                    title: "Noetic",
                    value: store.noetic?.globalCoherenceScore ?? 0,
                    footer: "Entropy Δ \(fmt(store.noetic?.entropyChange ?? 0))"
                )
            }
            if let mpgID = store.mpg.mpgID {
                Text("MPG \(mpgID): \(store.mpg.nodes.count) nodes · \(store.mpg.edges.count) edges")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var symbiosisPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Symbiosis")
                .font(.headline)
            let sym = store.symbiosis
            HStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Persona")
                        .font(.subheadline.weight(.semibold))
                    progressRow(label: "AtoZ", value: sym.persona.aToZArchivesFreshness)
                    progressRow(label: "Mentat", value: sym.persona.mentatRepositoryFreshness)
                    Text("Seldon: \(sym.persona.seldonPlanHorizon)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Divider().frame(height: 54)
                VStack(alignment: .leading, spacing: 4) {
                    Text("Synapse")
                        .font(.subheadline.weight(.semibold))
                    if let last = sym.synapseEvents.first {
                        Text("\(last.source) · \(last.channel.rawValue): \(last.message)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    } else {
                        Text("No recent events").font(.caption).foregroundStyle(.secondary)
                    }
                }
                Divider().frame(height: 54)
                VStack(alignment: .leading, spacing: 4) {
                    Text("Council")
                        .font(.subheadline.weight(.semibold))
                    Text(sym.lastCouncil.decision)
                        .font(.caption)
                    Text("Conf \(Int(sym.lastCouncil.confidence * 100))% · Dissent \(Int(sym.lastCouncil.dissent * 100))%")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Divider().frame(height: 54)
                VStack(alignment: .leading, spacing: 4) {
                    Text("Trinity Loop")
                        .font(.subheadline.weight(.semibold))
                    Text("Bio \(Int(sym.loop.bioDrift * 100)) · Sym \(Int(sym.loop.symbolicDrift * 100)) · Noe \(Int(sym.loop.noeticDrift * 100))")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text("Stability \(Int(sym.loop.stability * 100))%")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(12)
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
    }

    private func progressRow(label: String, value: Double) -> some View {
        let clamped = max(0, min(1, value))
        return HStack {
            Text(label).font(.caption2.weight(.semibold))
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.gray.opacity(0.2))
                    Capsule().fill(Color.accentColor.opacity(0.8))
                        .frame(width: CGFloat(clamped) * geo.size.width)
                }
            }
            .frame(height: 6)
            Text("\(Int(clamped * 100))%").font(.caption2).foregroundStyle(.secondary)
        }
    }

    private var cohortSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Coherence Wall (cohort)").font(.headline)
                Spacer()
                Button("Refresh Cohorts") { store.refreshCohorts() }.buttonStyle(.bordered)
                Button("Load Summary") {
                    if let id = selectedCohortID {
                        store.loadCohortSummary(cohortID: id, fromMs: 0, toMs: store.latestTRelMs + 60_000)
                        store.loadCohortEchoes(cohortID: id, fromMs: 0, toMs: store.latestTRelMs + 60_000)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(selectedCohortID == nil)
            }
            ScrollView(.horizontal) {
                HStack(spacing: 10) {
                    ForEach(store.cohorts) { cohort in
                        Button {
                            selectedCohortID = cohort.id
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(cohort.name).font(.headline)
                                Text("\(cohort.memberSessions.count) sessions").font(.caption).foregroundStyle(.secondary)
                            }
                            .padding(10)
                            .frame(width: 180, alignment: .leading)
                            .background(selectedCohortID == cohort.id ? Color.accentColor.opacity(0.15) : Color.clear)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        }.buttonStyle(.plain)
                    }
                }
            }
            if let summary = store.cohortSummary {
                Text("Loaded cohort \(summary.cohortID): \(summary.members.count) subjects").font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    private var timeline: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Timeline")
                    .font(.headline)
                Spacer()
                Picker("", selection: Binding(get: {
                    playback.mode
                }, set: { newMode in
                    if newMode == .live {
                        playback.resumeLive()
                        interaction.setMode(.live)
                    } else {
                        playback.mode = .replay
                        interaction.setMode(.replay)
                        Task { await loadReplayWindow(around: playback.tRelMs) }
                    }
                })) {
                    Text("Live").tag(H3LIXPlaybackController.Mode.live)
                    Text("Replay").tag(H3LIXPlaybackController.Mode.replay)
                }
                .pickerStyle(.segmented)
                .frame(width: 200)
            }

            TimelineBar(
                current: Binding(
                    get: { Double(playback.tRelMs) },
                    set: { newValue in
                        Task {
                            await loadReplayWindow(around: Int(newValue))
                            playback.seek(to: Int(newValue))
                        }
                    }
                ),
                duration: Double(max(playback.timelineMaxMs, store.latestTRelMs + 1_000)),
                markers: store.eventMarkers
            )

            HStack(spacing: 12) {
                Button(playback.isPlaying ? "Pause" : "Play") {
                    if playback.isPlaying {
                        playback.pause()
                    } else {
                        Task {
                            await loadReplayWindow(around: playback.tRelMs)
                            playback.play()
                        }
                    }
                }
                .buttonStyle(.bordered)

                Button("Step +1s") {
                    Task {
                        await loadReplayWindow(around: playback.tRelMs + 1_000)
                        playback.seek(to: playback.tRelMs + 1_000)
                    }
                }
                .buttonStyle(.bordered)

                Picker("Rate", selection: $playback.playbackRate) {
                    Text("0.25x").tag(0.25)
                    Text("1x").tag(1.0)
                    Text("2x").tag(2.0)
                }
                .pickerStyle(.segmented)
                .frame(width: 200)
                Spacer()
                Text("t = \(playback.tRelMs) ms")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var eventHud: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Events HUD")
                .font(.headline)
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Rogue Variable").font(.subheadline.weight(.semibold))
                    if let event = store.rogueEvents.first {
                        Text("ID \(event.rogueID) · potency \(fmt(event.potencyIndex))")
                        Text("Segments: \(event.segmentIDs?.joined(separator: ", ") ?? "—")")
                        Text("Impact: rate \(fmt(event.impactFactors.rateOfChange)) amp \(fmt(event.impactFactors.amplification))")
                        Button("Inspect Rogue") {
                            interaction.setMode(.rogueInspect(rogueId: event.rogueID))
                        }
                        .buttonStyle(.bordered)
                    } else {
                        Text("None yet").foregroundStyle(.secondary)
                    }
                }
                .padding(12)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

                VStack(alignment: .leading, spacing: 6) {
                    Text("MUFS").font(.subheadline.weight(.semibold))
                    if let event = store.mufsEvents.first {
                        Text("Decision \(event.decisionID)")
                        Text("Types: \(event.unawarenessTypes.map { $0.rawValue }.joined(separator: ", "))")
                        Text("Affected nodes: \(event.processUnawareNodeIds?.count ?? 0)")
                        Button("Inspect MUFS") {
                            interaction.setMode(.mufsInspect(decisionId: event.decisionID))
                        }
                        .buttonStyle(.bordered)
                    } else {
                        Text("None yet").foregroundStyle(.secondary)
                    }
                }
                .padding(12)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            }
        }
    }

    private var modeLabel: String {
        switch interaction.mode {
        case .live: return "Live"
        case .replay: return "Replay"
        case .rogueInspect(let id): return "Rogue Inspect \(id)"
        case .mufsInspect(let id): return "MUFS Inspect \(id)"
        }
    }

private func summaryTile(title: String, value: Double, footer: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.subheadline.weight(.semibold))
            Text(fmt(value))
                .font(.title3.monospacedDigit())
            Text(footer)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func loadReplayWindow(around center: Int, windowMs: Int = 10_000) async {
        let from = max(0, center - windowMs / 2)
        let to = center + windowMs / 2
        guard let sessionID = selectedSessionID ?? store.snapshot?.sessionID else { return }
        if playback.hasCache(for: from, to: to) { return }
        do {
            let replay = try await store.fetchReplay(sessionID: sessionID, fromMs: from, toMs: to)
            playback.setReplayFrames(replay.messages, range: from...to)
        } catch {
            // Surface errors via connection banner
            // keep connection state immutable; surface via banner/alert
            lastErrorMessage = "Replay load failed: \(error)"
            showErrorDetails = true
        }
    }

    private struct TimelineBar: View {
        @Binding var current: Double
        let duration: Double
        let markers: [TimelineMarker]

        var body: some View {
            let effectiveDuration = max(duration, 1)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.gray.opacity(0.2))
                    Capsule()
                        .fill(Color.accentColor)
                        .frame(width: max(0, min(CGFloat(current / effectiveDuration) * geo.size.width, geo.size.width)))
                    ForEach(markers.prefix(50)) { marker in
                        let x = CGFloat(Double(marker.tRelMs) / effectiveDuration) * geo.size.width
                        Capsule()
                            .fill(markerColor(marker.type))
                            .frame(width: 4, height: 16)
                            .position(x: x, y: geo.size.height / 2)
                    }
                    Circle()
                        .fill(Color.white)
                        .frame(width: 16, height: 16)
                        .overlay(Circle().stroke(Color.black.opacity(0.2)))
                        .offset(x: knobX(in: geo.size.width, duration: effectiveDuration))
                        .gesture(
                            DragGesture()
                                .onChanged { value in
                                    let clamped = max(0, min(value.location.x, geo.size.width))
                                    current = Double(clamped / geo.size.width) * effectiveDuration
                                }
                        )
                }
            }
            .frame(height: 22)
        }

        private func knobX(in width: CGFloat, duration: Double) -> CGFloat {
            max(0, min(CGFloat(current / duration) * width - 8, width - 8))
        }

        private func markerColor(_ type: TimelineMarkerType) -> Color {
            switch type {
            case .rogue: return .orange
            case .mufs: return .blue
            case .decision: return .purple
            }
        }
    }

    @MainActor
    private func toggleImmersiveSpace() async {
        isOpeningImmersive = true
        immersiveStatus = immersiveSpaceIsShown ? "Closing immersive..." : "Requesting immersive..."
        print("[H3LIX] toggleImmersiveSpace start showing=\(immersiveSpaceIsShown)")
        if immersiveSpaceIsShown {
            await dismissImmersiveSpace()
            immersiveSpaceIsShown = false
            print("[H3LIX] Immersive space dismissed id=\(immersiveSpaceID)")
            immersiveStatus = "Dismissed"
        } else {
            // Ensure we have content before entering immersive.
            if store.snapshot == nil, let preset = store.scenarioPresets.first {
                print("[H3LIX] No snapshot loaded; applying default scenario \(preset.id) before entering immersive.")
                immersiveStatus = "Applying default scenario before opening..."
                loadScenario(preset)
            }
            print("[H3LIX] Immersive space opening id=\(immersiveSpaceID)")
            let result = await openImmersiveSpace(id: immersiveSpaceID)
            switch result {
            case .opened:
                immersiveSpaceIsShown = true
                print("[H3LIX] Immersive space opened id=\(immersiveSpaceID)")
                immersiveStatus = "Opened"
            case .error:
                lastErrorMessage = "Immersive space failed to open."
                showErrorDetails = true
                print("[H3LIX] Immersive space error id=\(immersiveSpaceID)")
                immersiveStatus = "Failed to open"
            case .userCancelled:
                lastErrorMessage = "Opening immersive space was cancelled."
                showErrorDetails = true
                print("[H3LIX] Immersive space cancelled id=\(immersiveSpaceID)")
                immersiveStatus = "User cancelled"
            @unknown default:
                lastErrorMessage = "Immersive space could not open (state: \(String(describing: result)))."
                showErrorDetails = true
                print("[H3LIX] Immersive space unexpected result id=\(immersiveSpaceID) state=\(result)")
                immersiveStatus = "Unexpected state \(result)"
            }
        }
        print("[H3LIX] toggleImmersiveSpace end showing=\(immersiveSpaceIsShown)")
        isOpeningImmersive = false
        if immersiveSpaceIsShown == false, immersiveStatus == nil {
            immersiveStatus = "Not shown"
        }
    }
}

#elseif os(macOS)
import SwiftUI
import H3LIXState
import H3LIXCore

public struct DashboardView: View {
    @ObservedObject private var store: H3LIXStore
    @ObservedObject private var playback: H3LIXPlaybackController
    @ObservedObject private var interaction: H3LIXInteractionModel
    @ObservedObject private var teaching: TeachingStore
    @Binding private var immersiveSpaceIsShown: Bool
    @State private var selectedSessionID: String?
    @State private var selectedScenarioID: String?
    @State private var selectedCohortID: String?

    public init(store: H3LIXStore, playback: H3LIXPlaybackController, interaction: H3LIXInteractionModel, teaching: TeachingStore, immersiveSpaceIsShown: Binding<Bool>, immersiveSpaceID: String = "ImmersiveSpace") {
        self.store = store
        self.playback = playback
        self.interaction = interaction
        self.teaching = teaching
        self._immersiveSpaceIsShown = immersiveSpaceIsShown
    }

    public var body: some View {
        NavigationStack {
            ScrollView(.vertical) {
                VStack(alignment: .leading, spacing: 16) {
                    header
                    sessionSection
                    scenarioSection
                    cohortSection
                    statusSection
                    Text("Immersive space is available on visionOS. The macOS build provides data controls without immersive rendering.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(20)
            }
            .navigationTitle("H3LIX Desktop")
        }
        .onAppear {
            bootstrap()
        }
        .onChange(of: store.sessions) { sessions in
            if selectedSessionID == nil {
                selectedSessionID = sessions.first?.id
            }
        }
        .onChange(of: store.cohorts) { cohorts in
            if selectedCohortID == nil {
                selectedCohortID = cohorts.first?.id
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("H3LIX Desktop")
                .font(.largeTitle.weight(.bold))
            Text("Control sessions, load snapshots, and monitor state.")
                .foregroundStyle(.secondary)
                .font(.callout)
        }
    }

    private var sessionSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Sessions")
                    .font(.headline)
                Spacer()
                Button("Refresh") { store.refreshSessions() }
                    .buttonStyle(.bordered)
            }
            if store.sessions.isEmpty {
                Text("No sessions found yet. Refresh to pull from the API or use scenarios to seed demo data.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(store.sessions) { session in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(session.id).font(.subheadline.weight(.semibold))
                            Text("\(session.experimentID) · \(session.subjectID)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if selectedSessionID == session.id {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.accentColor)
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
                    .background(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(selectedSessionID == session.id ? Color.accentColor.opacity(0.12) : Color.white.opacity(0.04))
                    )
                    .onTapGesture {
                        selectedSessionID = session.id
                    }
                }
                HStack(spacing: 8) {
                    Button("Load Snapshot") {
                        if let id = selectedSessionID {
                            store.loadSnapshot(for: id)
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(selectedSessionID == nil)

                    Button("Start Stream") {
                        if let id = selectedSessionID {
                            store.startStream(sessionID: id)
                        }
                    }
                    .buttonStyle(.bordered)
                    .disabled(selectedSessionID == nil)

                    Button("Stop Stream") {
                        store.stopStream()
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var scenarioSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Scenarios")
                    .font(.headline)
                Spacer()
                if let activeID = selectedScenarioID,
                   let scenario = store.scenarioPresets.first(where: { $0.id == activeID }) {
                    Button("Apply \(scenario.title)") {
                        applyScenario(scenario)
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
            if store.scenarioPresets.isEmpty {
                Text("No scenario presets configured.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                Picker("Preset", selection: $selectedScenarioID) {
                    ForEach(store.scenarioPresets) { preset in
                        Text(preset.title).tag(Optional(preset.id))
                    }
                }
                .pickerStyle(.menu)
                Text("Scenarios repopulate the world without needing a backend.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var cohortSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Cohorts")
                    .font(.headline)
                Spacer()
                Button("Refresh") { store.refreshCohorts() }
                    .buttonStyle(.bordered)
            }
            if store.cohorts.isEmpty {
                Text("No cohorts yet.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                Picker("Select cohort", selection: $selectedCohortID) {
                    ForEach(store.cohorts) { cohort in
                        Text(cohort.name).tag(Optional(cohort.id))
                    }
                }
                .pickerStyle(.menu)
                HStack(spacing: 8) {
                    Button("Load Summary") {
                        if let cid = selectedCohortID {
                            store.loadCohortSummary(cohortID: cid, fromMs: 0, toMs: 60_000)
                        }
                    }
                    .buttonStyle(.bordered)
                    .disabled(selectedCohortID == nil)

                    Button("Load MPG Echoes") {
                        if let cid = selectedCohortID {
                            store.loadCohortEchoes(cohortID: cid, fromMs: 0, toMs: 60_000)
                        }
                    }
                    .buttonStyle(.bordered)
                    .disabled(selectedCohortID == nil)
                }
            }
        }
        .padding()
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var statusSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("State")
                .font(.headline)
            HStack {
                Label("\(store.mpg.baseSubgraph.nodes.count) nodes", systemImage: "circle.grid.3x3")
                Label("\(store.mpg.baseSubgraph.segments.count) segments", systemImage: "chart.bar.doc.horizontal")
                Label("\(store.rogueEvents.count) rogue events", systemImage: "flame")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            Text("Connection: \(statusLabel)")
                .font(.subheadline.weight(.semibold))
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var statusLabel: String {
        switch store.connectionState {
        case .idle:
            return "Idle"
        case .loadingSnapshot(let id):
            return "Loading snapshot \(id)..."
        case .streaming(let id):
            return "Streaming \(id)"
        case .error(let message):
            return "Error: \(message)"
        }
    }

    private func applyScenario(_ scenario: ScenarioPreset) {
        store.applyScenario(scenario)
        playback.resumeLive()
        playback.setLiveTime(scenario.snapshot.tRelMs)
        interaction.setMode(.live)
    }

    private func bootstrap() {
        if store.sessions.isEmpty {
            store.refreshSessions()
        }
        if store.cohorts.isEmpty {
            store.refreshCohorts()
        }
        if teaching.lessons.isEmpty {
            teaching.refreshLessons()
        }
        if selectedSessionID == nil {
            selectedSessionID = store.sessions.first?.id
        }
        if selectedCohortID == nil {
            selectedCohortID = store.cohorts.first?.id
        }
        if selectedScenarioID == nil {
            selectedScenarioID = store.scenarioPresets.first?.id
        }
        immersiveSpaceIsShown = false
    }
}
#endif
