import XCTest
@testable import H3LIXVisualState
@testable import H3LIXState
@testable import H3LIXCore

@MainActor
final class VisualStateBuilderTests: XCTestCase {
    func testHelixReflectsSomaticActivity() async throws {
        let builder = VisualStateBuilder()
        builder.start()

        let somatic = SomaticStatePayload(
            tRelMs: 1200,
            windowMs: 200,
            features: ["hrv": 0.6, "eda": 0.4],
            innovation: nil,
            covarianceDiag: nil,
            globalUncertaintyScore: 0.3,
            changePoint: true,
            anomalyScore: 0.8,
            anticipatoryMarkers: []
        )
        builder.ingest(somatic: somatic)

        try await Task.sleep(nanoseconds: 60_000_000)
        let snapshot = builder.snapshot
        builder.stop()

        XCTAssertGreaterThan(snapshot.helix.somatic.activity, 0.2)
        XCTAssertGreaterThan(snapshot.helix.somatic.anomaly, 0.2)
        XCTAssertEqual(snapshot.helix.timePlaneHeight, snapshot.helix.timePlaneHeight, "Should be finite value")
    }

    func testRogueOverlayMarksNodes() async throws {
        var graph = MpgGraphState()
        let node = MpgNode(
            id: "n1",
            label: "Node",
            description: nil,
            layerTags: [],
            metrics: .init(valence: 0.1, intensity: 0.5, recency: 0.2, stability: 0.7),
            confidence: 0.8,
            importance: 0.9,
            roles: [],
            evidencePreview: [],
            reasoningProvenance: nil
        )
        let segment = MpgSegment(
            id: "seg",
            label: "Segment",
            level: 0,
            memberNodeIds: ["n1"],
            cohesion: 0.5,
            averageImportance: 0.5,
            averageConfidence: 0.5,
            affectiveLoad: nil
        )
        graph.nodes[node.id] = node
        graph.segments[segment.id] = segment
        graph.level = 0

        let rogue = RogueVariableEventPayload(
            rogueID: "rv1",
            mpgID: "mpg",
            candidateType: "segment",
            levelRange: [0, 0],
            segmentIDs: ["seg"],
            pathwayNodes: nil,
            shapleyStats: .init(meanAbsContrib: 0.2, stdAbsContrib: 0.1, candidateAbsContrib: 0.3, zScore: 2),
            potencyIndex: 0.7,
            impactFactors: .init(rateOfChange: 0.4, breadthOfImpact: 0.5, amplification: 0.6, emotionalLoad: 0.2)
        )

        let builder = VisualStateBuilder()
        builder.start()
        builder.ingest(graph: graph)
        builder.ingest(rogue: rogue)

        try await Task.sleep(nanoseconds: 60_000_000)
        let snapshot = builder.snapshot
        builder.stop()

        XCTAssertEqual(snapshot.rogue?.activeSegmentIds, ["seg"])
        XCTAssertEqual(snapshot.mpg.nodes.first?.isRogueHotspot, true)
    }
}
