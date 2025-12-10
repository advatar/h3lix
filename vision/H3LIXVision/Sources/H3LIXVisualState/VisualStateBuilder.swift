import Foundation
import H3LIXCore
import H3LIXState

@MainActor
public final class VisualStateBuilder: ObservableObject {
    @Published public private(set) var snapshot: VisualSnapshot = .empty

    private var latestSomatic: SomaticStatePayload?
    private var latestSymbolic: SymbolicStatePayload?
    private var latestNoetic: NoeticStatePayload?
    private var latestDecision: DecisionCyclePayload?
    private var latestGraph: MpgGraphState = .init()
    private var latestRogue: RogueVariableEventPayload?
    private var latestMufs: MufsEventPayload?
    private var playbackTRelMs: Int?
    private var forcedRogueSegments: [String]?
    private var forcedMufsNodes: [String]?
    private var cohortSummary: CohortNoeticSummary?
    private var cohortEchoes: CohortMpgEchoResponse?

    private var timerTask: Task<Void, Never>?

    public init() {}

    public func start() {
        guard timerTask == nil else { return }
        print("[H3LIX] VisualStateBuilder start")
        timerTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                rebuildSnapshot()
                try? await Task.sleep(nanoseconds: 33_000_000) // ~30 Hz
            }
        }
    }

    public func stop() {
        timerTask?.cancel()
        timerTask = nil
    }

    public func ingest(somatic: SomaticStatePayload) {
        latestSomatic = somatic
    }

    public func ingest(symbolic: SymbolicStatePayload) {
        latestSymbolic = symbolic
    }

    public func ingest(noetic: NoeticStatePayload) {
        latestNoetic = noetic
    }

    public func ingest(decision: DecisionCyclePayload) {
        latestDecision = decision
    }

    public func ingest(graph: MpgGraphState) {
        latestGraph = graph
    }

    public func ingest(rogue: RogueVariableEventPayload) {
        latestRogue = rogue
    }

    public func ingest(mufs: MufsEventPayload) {
        latestMufs = mufs
    }

    public func setTimeOverride(tRelMs: Int?) {
        playbackTRelMs = tRelMs
    }

    public func setRogueOverride(segmentIds: [String]?) {
        forcedRogueSegments = segmentIds
    }

    public func setMufsOverride(nodeIds: [String]?) {
        forcedMufsNodes = nodeIds
    }

    public func setCohortSummary(summary: CohortNoeticSummary?, echoes: CohortMpgEchoResponse?) {
        cohortSummary = summary
        cohortEchoes = echoes
    }

    // MARK: - Build

    private func rebuildSnapshot() {
        let newHelix = buildHelix()
        let newHalo = buildHalo()
        let rogueOverlay = buildRogueOverlay()
        let mufsOverlay = buildMufsOverlay()
        let newMpg = VisualMappings.mpgVisual(from: latestGraph, rogue: rogueOverlay, mufs: mufsOverlay)
        let newSork = buildSork()
        let wall = VisualMappings.wallVisual(from: cohortSummary, echoes: cohortEchoes, currentTRelMs: playbackTRelMs)

        let newSnapshot = VisualSnapshot(
            helix: newHelix,
            halo: newHalo,
            mpg: newMpg,
            sork: newSork,
            rogue: rogueOverlay,
            mufs: mufsOverlay,
            wall: wall
        )

        snapshot = smooth(from: snapshot, to: newSnapshot, alpha: 0.2)
    }

    private func buildHelix() -> HelixVisualState {
        let somatic = latestSomatic
        let symbolic = latestSymbolic
        let noetic = latestNoetic
        let timeOverride = playbackTRelMs

        let somaticActivity = VisualMappings.normalizeActivity(somatic?.features.values.map { $0 } ?? [], scale: 0.7)
        let somaticUncertainty = Float(VisualMappings.clamp(somatic?.globalUncertaintyScore ?? 0, max: 1))
        let somaticAnomaly = VisualMappings.anomaly(somatic?.anomalyScore, changePoint: somatic?.changePoint ?? false)

        let symbolicActivity = VisualMappings.normalizeActivity(symbolic?.beliefs.map { $0.importance } ?? [], scale: 1.0)
        let symbolicUncertainty = VisualMappings.normalizeActivity(symbolic?.predictions.map { 1 - ($0.topk.first?.probability ?? 0) } ?? [], scale: 1.0)
        let symbolicAnomaly: Float = symbolic?.uncertaintyRegions.isEmpty == false ? 0.4 : 0.1

        let noeticActivity = Float(VisualMappings.clamp(noetic?.globalCoherenceScore ?? 0, max: 1))
        let noeticUncertainty = Float(VisualMappings.clamp(abs(noetic?.entropyChange ?? 0) / 2.0, max: 1))
        let noeticAnomaly = Float(VisualMappings.clamp(abs(noetic?.entropyChange ?? 0) / 3.0, max: 1))

        let timePlane = VisualMappings.timePlaneHeight(tRelMs: timeOverride ?? somatic?.tRelMs ?? noetic?.tRelMs)

        return HelixVisualState(
            timePlaneHeight: timePlane,
            somatic: .init(activity: somaticActivity, anomaly: somaticAnomaly, uncertainty: somaticUncertainty),
            symbolic: .init(activity: symbolicActivity, anomaly: symbolicAnomaly, uncertainty: symbolicUncertainty),
            noetic: .init(activity: noeticActivity, anomaly: noeticAnomaly, uncertainty: noeticUncertainty)
        )
    }

    private func buildHalo() -> HaloVisualState {
        let noetic = latestNoetic
        let global = Float(VisualMappings.clamp(noetic?.globalCoherenceScore ?? 0, max: 1))
        let entropy = noetic?.entropyChange ?? 0
        let bands = VisualMappings.haloBands(from: noetic?.coherenceSpectrum ?? [], entropyChange: entropy)
        let pulse = Float(VisualMappings.clamp(noetic?.intuitiveAccuracyEstimate?.pBetterThanBaseline ?? 0, max: 1))
        return HaloVisualState(globalCoherence: global, bands: bands, pulse: pulse)
    }

    private func buildRogueOverlay() -> RogueOverlayState? {
        if let forced = forcedRogueSegments {
            return RogueOverlayState(activeSegmentIds: forced)
        }
        guard let latestRogue else { return nil }
        if let segmentIDs = latestRogue.segmentIDs {
            return RogueOverlayState(activeSegmentIds: segmentIDs)
        }
        return nil
    }

    private func buildMufsOverlay() -> MufsOverlayState? {
        if let forced = forcedMufsNodes {
            return MufsOverlayState(hasMufs: true, affectedNodeIds: forced)
        }
        guard let latestMufs else { return nil }
        let affected = latestMufs.processUnawareNodeIds ?? []
        return MufsOverlayState(hasMufs: true, affectedNodeIds: affected)
    }

    private func buildSork() -> SorkVisualState {
        let phaseLabel = latestDecision?.phase
        let phases = VisualMappings.sorkPhases(active: phaseLabel)
        let comet = VisualMappings.cometAngle(for: phaseLabel ?? "S", previousAngle: snapshot.sork.cometAngle)
        return SorkVisualState(cometAngle: comet, phases: phases)
    }

    // MARK: - Smoothing

    private func smooth(from: VisualSnapshot, to: VisualSnapshot, alpha: Float) -> VisualSnapshot {
        VisualSnapshot(
            helix: smoothHelix(from: from.helix, to: to.helix, alpha: alpha),
            halo: smoothHalo(from: from.halo, to: to.halo, alpha: alpha),
            mpg: to.mpg, // MPG positions should stay deterministic; skip smoothing to avoid drift.
            sork: smoothSork(from: from.sork, to: to.sork, alpha: alpha),
            rogue: to.rogue,
            mufs: to.mufs,
            wall: to.wall
        )
    }

    private func smoothHelix(from: HelixVisualState, to: HelixVisualState, alpha: Float) -> HelixVisualState {
        HelixVisualState(
            timePlaneHeight: VisualMappings.smoothStep(from.timePlaneHeight, to.timePlaneHeight, alpha: alpha),
            somatic: smoothRibbon(from: from.somatic, to: to.somatic, alpha: alpha),
            symbolic: smoothRibbon(from: from.symbolic, to: to.symbolic, alpha: alpha),
            noetic: smoothRibbon(from: from.noetic, to: to.noetic, alpha: alpha)
        )
    }

    private func smoothRibbon(from: HelixRibbonState, to: HelixRibbonState, alpha: Float) -> HelixRibbonState {
        HelixRibbonState(
            activity: VisualMappings.smoothStep(from.activity, to.activity, alpha: alpha),
            anomaly: VisualMappings.smoothStep(from.anomaly, to.anomaly, alpha: alpha),
            uncertainty: VisualMappings.smoothStep(from.uncertainty, to.uncertainty, alpha: alpha)
        )
    }

    private func smoothHalo(from: HaloVisualState, to: HaloVisualState, alpha: Float) -> HaloVisualState {
        let bands = zip(from.bands, to.bands).map { (lhs, rhs) -> HaloBandState in
            HaloBandState(
                intensity: VisualMappings.smoothStep(lhs.intensity, rhs.intensity, alpha: alpha),
                turbulence: VisualMappings.smoothStep(lhs.turbulence, rhs.turbulence, alpha: alpha)
            )
        } + to.bands.dropFirst(from.bands.count)

        return HaloVisualState(
            globalCoherence: VisualMappings.smoothStep(from.globalCoherence, to.globalCoherence, alpha: alpha),
            bands: bands,
            pulse: VisualMappings.smoothStep(from.pulse, to.pulse, alpha: alpha)
        )
    }

    private func smoothSork(from: SorkVisualState, to: SorkVisualState, alpha: Float) -> SorkVisualState {
        let phases = zip(from.phases, to.phases).map { (lhs, rhs) -> SorkPhaseState in
            SorkPhaseState(
                active: rhs.active,
                intensity: VisualMappings.smoothStep(lhs.intensity, rhs.intensity, alpha: alpha)
            )
        } + to.phases.dropFirst(from.phases.count)

        return SorkVisualState(
            cometAngle: VisualMappings.smoothStep(from.cometAngle, to.cometAngle, alpha: alpha),
            phases: phases
        )
    }
}
