#if os(visionOS)
import SwiftUI
import H3LIXState
import H3LIXCore

struct SelectionHUDView: View {
    @ObservedObject var store: H3LIXStore
    @ObservedObject var interaction: H3LIXInteractionModel

    var body: some View {
        Group {
            switch interaction.selection {
            case .none:
                EmptyView()
            case .mpgNode(let nodeId):
                if let node = store.mpg.nodes[nodeId] {
                    nodeHUD(node)
                }
            case .mpgSegment(let segmentId):
                if let segment = store.mpg.segments[segmentId] {
                    segmentHUD(segment)
                }
            case .rogueCluster(let segmentId):
                rogueHUD(segmentId)
            case .mufsDecision(let decisionId):
                mufsHUD(decisionId)
        case .helixLayer(let layer):
            layerHUD(layer)
        case .sorkPhase(let phase):
            phaseHUD(phase)
        case .cohortSubject(let sessionId):
            cohortSubjectHUD(sessionId)
        case .cohortGroup:
            cohortGroupHUD()
        }
    }
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .padding(10)
        .frame(maxWidth: 320, alignment: .leading)
    }

    private func nodeHUD(_ node: MpgNode) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(node.label).font(.headline)
            Text(node.description ?? "").font(.caption).foregroundStyle(.secondary)
            Text("Conf \(fmt(node.confidence)) · Imp \(fmt(node.importance))").font(.caption.monospacedDigit())
            Text("Valence \(fmt(node.metrics.valence)) · Stability \(fmt(node.metrics.stability))").font(.caption2)
            if !node.roles.isEmpty {
                let roles = node.roles.joined(separator: ", ")
                Text("Roles: \(roles)").font(.caption2)
            }
            Button("Close") { interaction.select(.none) }.buttonStyle(.bordered)
        }
    }

    private func segmentHUD(_ segment: MpgSegment) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(segment.label).font(.headline)
            Text("Cohesion \(fmt(segment.cohesion)) · Size \(segment.memberNodeIds.count)").font(.caption)
            Button("Close") { interaction.select(.none) }.buttonStyle(.bordered)
        }
    }

    private func rogueHUD(_ segmentId: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Rogue Variable").font(.headline)
            if let event = store.rogueEvents.first(where: { $0.segmentIDs?.contains(segmentId) == true }) {
                Text("ID \(event.rogueID)").font(.subheadline)
                Text("Potency \(fmt(event.potencyIndex))").font(.caption)
                Text("RoC \(fmt(event.impactFactors.rateOfChange)) · Amp \(fmt(event.impactFactors.amplification))").font(.caption2)
            } else {
                Text("Segment \(segmentId)").font(.caption)
            }
            Button("Close") { interaction.select(.none) }.buttonStyle(.bordered)
        }
    }

    private func mufsHUD(_ decisionId: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("MUFS").font(.headline)
            if let event = store.mufsEvents.first(where: { $0.decisionID == decisionId }) {
                Text("Decision \(event.decisionID)").font(.subheadline)
                let types = event.unawarenessTypes.map { $0.rawValue }.joined(separator: ", ")
                Text("Types: \(types)").font(.caption)
                Text("Affected nodes: \(event.processUnawareNodeIds?.count ?? 0)").font(.caption2)
            } else {
                Text("Decision \(decisionId)").font(.caption)
            }
            Button("Close") { interaction.select(.none) }.buttonStyle(.bordered)
        }
    }

    private func layerHUD(_ layer: HelixLayerType) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("\(layerDisplay(layer)) layer").font(.headline)
            Text("Recent t = \(store.latestTRelMs) ms").font(.caption)
            Button("Close") { interaction.select(.none) }.buttonStyle(.bordered)
        }
    }

    private func phaseHUD(_ phase: SorkPhase) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("SORK phase \(phaseDisplay(phase))").font(.headline)
            if let decision = store.decisionCycle {
                Text("Decision \(decision.decisionID ?? "—")").font(.caption)
                Text("Phase \(decision.phase)").font(.caption2)
            }
            Button("Close") { interaction.select(.none) }.buttonStyle(.bordered)
        }
    }

    private func cohortSubjectHUD(_ sessionId: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Subject \(sessionId)").font(.headline)
            Text("Tap to focus this subject in dashboard").font(.caption)
            HStack {
                Button("Load snapshot") {
                    interaction.select(.none)
                    store.loadSnapshot(for: sessionId)
                }
                .buttonStyle(.bordered)
                Button("Start stream") {
                    interaction.select(.none)
                    store.startStream(sessionID: sessionId)
                }
                .buttonStyle(.bordered)
            }
            Button("Close") { interaction.select(.none) }.buttonStyle(.bordered)
        }
    }

    private func cohortGroupHUD() -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Group Coherence").font(.headline)
            if let summary = store.cohortSummary {
                Text("Subjects: \(summary.members.count)").font(.caption)
                if let mean = summary.group.last?.meanGlobalCoherence {
                    Text("Mean coherence: \(fmt(mean))").font(.caption2)
                }
            }
            Button("Close") { interaction.select(.none) }.buttonStyle(.bordered)
        }
    }

    private func fmt(_ value: Double) -> String {
        value.formatted(.number.precision(.fractionLength(2)))
    }

    private func layerDisplay(_ layer: HelixLayerType) -> String {
        switch layer {
        case .somatic: return "Somatic"
        case .symbolic: return "Symbolic"
        case .noetic: return "Noetic"
        }
    }

    private func phaseDisplay(_ phase: SorkPhase) -> String {
        switch phase {
        case .S: return "S"
        case .O: return "O"
        case .R: return "R"
        case .K: return "K"
        case .N: return "N"
        case .SPrime: return "S′"
        }
    }
}
#endif
