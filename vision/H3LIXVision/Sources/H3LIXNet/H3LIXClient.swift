import Foundation
import H3LIXCore

public enum H3LIXClientError: Error {
    case invalidURL
    case badStatus(Int)
    case decodingFailed(Error)
    case encodingFailed
    case streamClosed
}

public actor H3LIXClient {
    public struct Configuration {
        public var baseURL: URL
        public var session: URLSession
        public var additionalHeaders: [String: String]

        public init(
            baseURL: URL = URL(string: "http://localhost:8000")!,
            session: URLSession = .shared,
            additionalHeaders: [String: String] = [:]
        ) {
            self.baseURL = baseURL
            self.session = session
            self.additionalHeaders = additionalHeaders
        }
    }

    private let config: Configuration
    private var streamTask: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?
    private var pingTask: Task<Void, Never>?

    public init(configuration: Configuration = Configuration()) {
        self.config = configuration
    }

    // MARK: - REST

    public func fetchSessions() async throws -> [SessionSummary] {
        let url = config.baseURL.appendingPathComponent("v1/sessions")
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw H3LIXClientError.badStatus(-1)
        }
        guard (200..<300).contains(http.statusCode) else {
            throw H3LIXClientError.badStatus(http.statusCode)
        }
        do {
            return try decoder().decode([SessionSummary].self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    public func fetchSnapshot(sessionID: String) async throws -> SnapshotResponse {
        let url = config.baseURL
            .appendingPathComponent("v1/sessions")
            .appendingPathComponent(sessionID)
            .appendingPathComponent("snapshot")
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw H3LIXClientError.badStatus(-1)
        }
        guard (200..<300).contains(http.statusCode) else {
            throw H3LIXClientError.badStatus(http.statusCode)
        }
        do {
            return try decoder().decode(SnapshotResponse.self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    public func fetchReplay(sessionID: String, fromMs: Int, toMs: Int) async throws -> ReplayResponse {
        let url = config.baseURL
            .appendingPathComponent("v1/sessions")
            .appendingPathComponent(sessionID)
            .appendingPathComponent("replay")
            .appending(queryItems: [
                URLQueryItem(name: "from_ms", value: "\(fromMs)"),
                URLQueryItem(name: "to_ms", value: "\(toMs)")
            ])
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw H3LIXClientError.badStatus(-1)
        }
        guard (200..<300).contains(http.statusCode) else {
            throw H3LIXClientError.badStatus(http.statusCode)
        }
        do {
            return try decoder().decode(ReplayResponse.self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    // MARK: - Cohorts

    public func listCohorts() async throws -> [Cohort] {
        let url = config.baseURL.appendingPathComponent("v1/cohorts")
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
        do {
            return try decoder().decode([Cohort].self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    public func fetchCohortNoeticSummary(cohortID: String, fromMs: Int, toMs: Int, binMs: Int = 1_000) async throws -> CohortNoeticSummary {
        var components = URLComponents(url: config.baseURL
            .appendingPathComponent("v1/cohorts")
            .appendingPathComponent(cohortID)
            .appendingPathComponent("noetic-summary"), resolvingAgainstBaseURL: false)
        components?.queryItems = [
            URLQueryItem(name: "from_ms", value: "\(fromMs)"),
            URLQueryItem(name: "to_ms", value: "\(toMs)"),
            URLQueryItem(name: "bin_ms", value: "\(binMs)")
        ]
        guard let url = components?.url else { throw H3LIXClientError.invalidURL }
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
        do {
            return try decoder().decode(CohortNoeticSummary.self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    public func fetchCohortMpgEchoes(cohortID: String, fromMs: Int, toMs: Int, minConsistency: Double = 0.7) async throws -> CohortMpgEchoResponse {
        var components = URLComponents(url: config.baseURL
            .appendingPathComponent("v1/cohorts")
            .appendingPathComponent(cohortID)
            .appendingPathComponent("mpg-echoes"), resolvingAgainstBaseURL: false)
        components?.queryItems = [
            URLQueryItem(name: "from_ms", value: "\(fromMs)"),
            URLQueryItem(name: "to_ms", value: "\(toMs)"),
            URLQueryItem(name: "min_consistency", value: "\(minConsistency)")
        ]
        guard let url = components?.url else { throw H3LIXClientError.invalidURL }
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
        do {
            return try decoder().decode(CohortMpgEchoResponse.self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    // MARK: - Lessons / Teaching

    public func listLessons() async throws -> [Lesson] {
        let url = config.baseURL.appendingPathComponent("v1/lessons")
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
        do {
            return try decoder().decode([Lesson].self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    public func fetchLesson(id: String) async throws -> Lesson {
        let url = config.baseURL
            .appendingPathComponent("v1/lessons")
            .appendingPathComponent(id)
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
        do {
            return try decoder().decode(Lesson.self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    public func fetchLessonProgress(lessonID: String, userID: String) async throws -> LessonProgress {
        let url = config.baseURL
            .appendingPathComponent("v1/lessons")
            .appendingPathComponent(lessonID)
            .appendingPathComponent("progress")
            .appendingPathComponent(userID)
        let request = try makeRequest(url: url, method: "GET")
        let (data, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
        do {
            return try decoder().decode(LessonProgress.self, from: data)
        } catch {
            throw H3LIXClientError.decodingFailed(error)
        }
    }

    public func updateLessonProgress(_ progress: LessonProgress) async throws {
        let url = config.baseURL
            .appendingPathComponent("v1/lessons")
            .appendingPathComponent(progress.lessonID)
            .appendingPathComponent("progress")
            .appendingPathComponent(progress.userID)
        var request = try makeRequest(url: url, method: "POST")
        do {
            request.httpBody = try JSONEncoder().encode(progress)
        } catch {
            throw H3LIXClientError.encodingFailed
        }
        let (_, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
    }

    // MARK: - Consent / Ingestion

    public func setConsent(participantID: String, scopes: [String]) async throws {
        let url = config.baseURL
            .appendingPathComponent("consent")
            .appendingPathComponent("participant")
        var request = try makeRequest(url: url, method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ConsentUpdateRequest(participantID: participantID, scopes: scopes)
        request.httpBody = try encoder().encode(body)
        let (_, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
    }

    @discardableResult
    public func ingestSomaticSamples(
        participantID: String,
        sessionID: String,
        samples: [SomaticSampleInput],
        source: String = "visionpro-healthkit"
    ) async throws -> Int {
        guard !samples.isEmpty else { return 0 }
        let events = samples.map { sample in
            EventEnvelopeInput(
                participantID: participantID,
                source: source,
                streamType: .somatic,
                timestampUTC: sample.timestampUTC,
                sessionID: sessionID,
                payload: SomaticEventPayload(samples: [sample])
            )
        }
        let batch = EventBatchInput(events: events)
        let url = config.baseURL
            .appendingPathComponent("streams")
            .appendingPathComponent("events")
        var request = try makeRequest(url: url, method: "POST")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder().encode(batch)
        let (_, response) = try await config.session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw H3LIXClientError.badStatus(-1) }
        guard (200..<300).contains(http.statusCode) else { throw H3LIXClientError.badStatus(http.statusCode) }
        return events.count
    }

    // MARK: - Stream

    public func openStream(
        sessionID: String,
        messageTypes: [MessageType] = MessageType.allCases,
        onEvent: @escaping @Sendable (AnyTelemetryEnvelope) -> Void,
        onClose: @escaping @Sendable () -> Void = {}
    ) async throws {
        await closeStream()

        let url = config.baseURL
            .appendingPathComponent("v1")
            .appendingPathComponent("stream")
        var request = try makeRequest(url: url, method: "GET")
        let task = config.session.webSocketTask(with: request)
        streamTask = task
        task.resume()

        let payload: [String: Any] = [
            "type": "subscribe",
            "session_id": sessionID,
            "message_types": messageTypes.map(\.rawValue)
        ]
        let data = try JSONSerialization.data(withJSONObject: payload, options: [])
        try await task.send(.data(data))

        listenForMessages(task: task, onEvent: onEvent, onClose: onClose)
        schedulePing(task: task)
    }

    public func closeStream() async {
        receiveTask?.cancel()
        pingTask?.cancel()
        receiveTask = nil
        pingTask = nil
        guard let task = streamTask else { return }
        task.cancel(with: .goingAway, reason: nil)
        streamTask = nil
    }

    // MARK: - Helpers

    private func listenForMessages(
        task: URLSessionWebSocketTask,
        onEvent: @escaping @Sendable (AnyTelemetryEnvelope) -> Void,
        onClose: @escaping @Sendable () -> Void
    ) {
        receiveTask?.cancel()
        receiveTask = Task { [weak self, decoder = decoder()] in
            while true {
                do {
                    let message = try await task.receive()
                    let data: Data
                    switch message {
                    case .data(let raw):
                        data = raw
                    case .string(let string):
                        guard let converted = string.data(using: .utf8) else { continue }
                        data = converted
                    @unknown default:
                        continue
                    }

                    if let envelope = try? decoder.decode(AnyTelemetryEnvelope.self, from: data) {
                        await MainActor.run {
                            onEvent(envelope)
                        }
                    }
                } catch {
                    await self?.streamDidClose()
                    await MainActor.run {
                        onClose()
                    }
                    break
                }
            }
        }
    }

    private func schedulePing(task: URLSessionWebSocketTask) {
        pingTask?.cancel()
        pingTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 20_000_000_000)
                await self?.sendPing()
            }
        }
    }

    private func sendPing() async {
        guard let task = streamTask else { return }
        task.sendPing { [weak self] error in
            if error != nil {
                Task { await self?.streamDidClose() }
            }
        }
    }

    private func streamDidClose() async {
        receiveTask?.cancel()
        pingTask?.cancel()
        receiveTask = nil
        pingTask = nil
        streamTask?.cancel(with: .goingAway, reason: nil)
        streamTask = nil
    }

    private func decoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }

    private func encoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        return encoder
    }

    private func makeRequest(url: URL, method: String) throws -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = method
        config.additionalHeaders.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }
        return request
    }
}
