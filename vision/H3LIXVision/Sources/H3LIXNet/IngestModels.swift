import Foundation
import H3LIXCore

public struct SomaticSampleInput: Codable, Hashable, Sendable {
    public let channel: String
    public let value: Double
    public let timestampUTC: String

    public init(channel: String, value: Double, timestampUTC: String) {
        self.channel = channel
        self.value = value
        self.timestampUTC = timestampUTC
    }

    enum CodingKeys: String, CodingKey {
        case channel
        case value
        case timestampUTC = "timestamp_utc"
    }
}

public struct SomaticEventPayload: Codable, Hashable, Sendable {
    public let samples: [SomaticSampleInput]

    public init(samples: [SomaticSampleInput]) {
        self.samples = samples
    }
}

public struct EventEnvelopeInput<Payload: Codable & Sendable>: Codable, Sendable {
    public let participantID: String
    public let source: String
    public let streamType: StreamType
    public let timestampUTC: String
    public let sessionID: String?
    public let payload: Payload

    public init(
        participantID: String,
        source: String,
        streamType: StreamType,
        timestampUTC: String,
        sessionID: String?,
        payload: Payload
    ) {
        self.participantID = participantID
        self.source = source
        self.streamType = streamType
        self.timestampUTC = timestampUTC
        self.sessionID = sessionID
        self.payload = payload
    }

    enum CodingKeys: String, CodingKey {
        case participantID = "participant_id"
        case source
        case streamType = "stream_type"
        case timestampUTC = "timestamp_utc"
        case sessionID = "session_id"
        case payload
    }
}

public struct EventBatchInput<Payload: Codable & Sendable>: Codable, Sendable {
    public let events: [EventEnvelopeInput<Payload>]

    public init(events: [EventEnvelopeInput<Payload>]) {
        self.events = events
    }
}

struct ConsentUpdateRequest: Codable, Sendable {
    let participantID: String
    let scopes: [String]

    enum CodingKeys: String, CodingKey {
        case participantID = "participant_id"
        case scopes
    }
}
