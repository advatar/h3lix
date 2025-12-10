import Foundation
import H3LIXCore

#if canImport(HealthKit) && os(visionOS)
import HealthKit

@MainActor
public final class HealthKitStreamer {
    private let healthStore = HKHealthStore()
    private let client: H3LIXClient
    private let participantID: String
    private let sessionID: String
    private let typeIdentifiers: [HKQuantityTypeIdentifier]
    private var queries: [HKQuery] = []
    private let anchorStoreKey = "HealthKitStreamer.anchors"
    @MainActor private var anchors: [HKQuantityTypeIdentifier: HKQueryAnchor] = [:]
    private let isoFormatter: ISO8601DateFormatter = {
        let fmt = ISO8601DateFormatter()
        fmt.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fmt
    }()

    public init(
        client: H3LIXClient,
        participantID: String,
        sessionID: String,
        typeIdentifiers: [HKQuantityTypeIdentifier]? = nil
    ) {
        self.client = client
        self.participantID = participantID
        self.sessionID = sessionID
        self.typeIdentifiers = typeIdentifiers ?? [
            .heartRate,
            .restingHeartRate,
            .respiratoryRate,
            .oxygenSaturation,
            .stepCount,
            .distanceWalkingRunning,
            .distanceCycling,
            .basalEnergyBurned,
            .activeEnergyBurned
        ]
        loadAnchors()
    }

    public func requestAuthorization() async throws {
        let types = Set(typeIdentifiers.compactMap { HKObjectType.quantityType(forIdentifier: $0) })
        try await healthStore.requestAuthorization(toShare: [], read: types)
    }

    public func startStreaming() async throws {
        try await requestAuthorization()
        try await client.setConsent(participantID: participantID, scopes: ["wearables"])
        queries = typeIdentifiers.compactMap { createQuery(for: $0) }
        queries.forEach { healthStore.execute($0) }
    }

    public func stop() {
        queries.forEach { healthStore.stop($0) }
        queries.removeAll()
    }

    private func createQuery(for typeID: HKQuantityTypeIdentifier) -> HKAnchoredObjectQuery? {
        guard let qType = HKObjectType.quantityType(forIdentifier: typeID) else { return nil }
        let initialAnchor: HKQueryAnchor? = {
            if Thread.isMainThread {
                return anchors[typeID]
            }
            // Should not happen, but keep access safe.
            return nil
        }()
        let handler: @Sendable (HKAnchoredObjectQuery, [HKSample]?, [HKDeletedObject]?, HKQueryAnchor?, Error?) -> Void = { [weak self] _, samples, _, newAnchor, error in
            guard let self else { return }
            guard error == nil, let samples = samples as? [HKQuantitySample], !samples.isEmpty else { return }
            if let newAnchor {
                Task { @MainActor in
                    self.anchors[typeID] = newAnchor
                    self.persistAnchors()
                }
            }
            Task {
                await self.ingest(samples: samples, typeID: typeID)
            }
        }
        let query = HKAnchoredObjectQuery(type: qType, predicate: nil, anchor: initialAnchor, limit: HKObjectQueryNoLimit, resultsHandler: handler)
        query.updateHandler = handler
        return query
    }

    @MainActor
    private func ingest(samples: [HKQuantitySample], typeID: HKQuantityTypeIdentifier) async {
        let payloadSamples: [SomaticSampleInput] = samples.compactMap { sample in
            guard let channel = channel(for: typeID), let value = value(sample, for: typeID) else { return nil }
            let ts = isoFormatter.string(from: sample.startDate)
            return SomaticSampleInput(channel: channel, value: value, timestampUTC: ts)
        }
        guard !payloadSamples.isEmpty else { return }
        let client = client
        let participantID = participantID
        let sessionID = sessionID
        Task.detached { [payloadSamples] in
            _ = try? await client.ingestSomaticSamples(
                participantID: participantID,
                sessionID: sessionID,
                samples: payloadSamples,
                source: "visionpro-healthkit"
            )
        }
    }

    private func channel(for typeID: HKQuantityTypeIdentifier) -> String? {
        switch typeID {
        case .heartRate: return "heart_rate_bpm"
        case .restingHeartRate: return "resting_hr_bpm"
        case .respiratoryRate: return "resp_rate_bpm"
        case .oxygenSaturation: return "spo2_pct"
        case .stepCount: return "step_count"
        case .distanceWalkingRunning: return "distance_m"
        case .distanceCycling: return "distance_cycling_m"
        case .basalEnergyBurned: return "basal_energy_kcal"
        case .activeEnergyBurned: return "active_energy_kcal"
        default: return nil
        }
    }

    private func value(_ sample: HKQuantitySample, for typeID: HKQuantityTypeIdentifier) -> Double? {
        switch typeID {
        case .heartRate, .restingHeartRate:
            return sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
        case .respiratoryRate:
            return sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
        case .oxygenSaturation:
            return sample.quantity.doubleValue(for: HKUnit.percent())
        case .stepCount:
            return sample.quantity.doubleValue(for: HKUnit.count())
        case .distanceWalkingRunning, .distanceCycling:
            return sample.quantity.doubleValue(for: HKUnit.meter())
        case .basalEnergyBurned, .activeEnergyBurned:
            return sample.quantity.doubleValue(for: HKUnit.kilocalorie())
        default:
            return nil
        }
    }

    // Persist anchors so incremental queries survive app restarts.
    @MainActor
    private func persistAnchors() {
        var encoded: [String: Data] = [:]
        for (typeID, anchor) in anchors {
            if let data = try? NSKeyedArchiver.archivedData(withRootObject: anchor, requiringSecureCoding: true) {
                encoded[typeID.rawValue] = data
            }
        }
        UserDefaults.standard.set(encoded, forKey: anchorStoreKey)
    }

    @MainActor
    private func loadAnchors() {
        guard let stored = UserDefaults.standard.dictionary(forKey: anchorStoreKey) as? [String: Data] else { return }
        var loaded: [HKQuantityTypeIdentifier: HKQueryAnchor] = [:]
        for (raw, data) in stored {
            let typeID = HKQuantityTypeIdentifier(rawValue: raw)
            guard HKObjectType.quantityType(forIdentifier: typeID) != nil,
                  let anchor = try? NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: data) else { continue }
            loaded[typeID] = anchor
        }
        anchors = loaded
    }
}
#else

public enum HealthKitStreamerError: Error {
    case unsupportedPlatform
}

public typealias HKQuantityTypeIdentifier = String

@MainActor
public final class HealthKitStreamer {
    public init(
        client: H3LIXClient,
        participantID: String,
        sessionID: String,
        typeIdentifiers: [HKQuantityTypeIdentifier]? = nil
    ) {
        _ = (client, participantID, sessionID, typeIdentifiers)
    }

    public func requestAuthorization() async throws {
        throw HealthKitStreamerError.unsupportedPlatform
    }

    public func startStreaming() async throws {
        throw HealthKitStreamerError.unsupportedPlatform
    }

    public func stop() {}
}

#endif
