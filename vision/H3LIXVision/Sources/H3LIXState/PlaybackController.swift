import Foundation
import H3LIXCore

@MainActor
public final class H3LIXPlaybackController: ObservableObject {
    public enum Mode {
        case live
        case replay
    }

    @Published public var mode: Mode = .live
    @Published public var tRelMs: Int = 0
    @Published public var isPlaying: Bool = false
    @Published public var playbackRate: Double = 1.0
    @Published public var timelineMaxMs: Int = 60_000

    public var onReplayEnvelopes: (([AnyTelemetryEnvelope]) -> Void)?

    private var timerTask: Task<Void, Never>?
    private var replayFrames: [ReplayFrame] = []
    private var lastDeliveredIndex: Int = 0
    private var referenceDate: Date?
    private var cachedRange: ClosedRange<Int>?

    public init() {}

    public func setLiveTime(_ t: Int) {
        guard mode == .live else { return }
        tRelMs = t
        timelineMaxMs = max(timelineMaxMs, t + 1_000)
    }

    public func seek(to newT: Int) {
        mode = .replay
        tRelMs = max(0, newT)
        deliverFrames(upTo: tRelMs)
    }

    public func play() {
        mode = .replay
        isPlaying = true
        startTimerIfNeeded()
    }

    public func pause() {
        isPlaying = false
        timerTask?.cancel()
        timerTask = nil
    }

    public func resumeLive() {
        pause()
        mode = .live
        lastDeliveredIndex = 0
        replayFrames.removeAll()
    }

    public func hasCache(for from: Int, to: Int) -> Bool {
        guard let cached = cachedRange else { return false }
        return from >= cached.lowerBound && to <= cached.upperBound
    }

    public func setReplayFrames(_ frames: [AnyTelemetryEnvelope], range: ClosedRange<Int>) {
        let mapped = frames.compactMap { frame -> ReplayFrame? in
            ReplayFrame(envelope: frame, tRelMs: payloadTRelMs(from: frame) ?? inferredTRelMs(from: frame))
        }.sorted(by: { $0.tRelMs < $1.tRelMs })
        replayFrames = mapped
        cachedRange = range
        lastDeliveredIndex = 0
    }

    private func startTimerIfNeeded() {
        guard timerTask == nil else { return }
        timerTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                if self.isPlaying {
                    let step = Int(33.0 * self.playbackRate)
                    self.tRelMs += step
                    if self.mode == .replay {
                        self.deliverFrames(upTo: self.tRelMs)
                    }
                }
                try? await Task.sleep(nanoseconds: 33_000_000)
            }
        }
    }

    private func deliverFrames(upTo t: Int) {
        guard mode == .replay, !replayFrames.isEmpty else { return }
        var delivered: [AnyTelemetryEnvelope] = []
        while lastDeliveredIndex < replayFrames.count, replayFrames[lastDeliveredIndex].tRelMs <= t {
            delivered.append(replayFrames[lastDeliveredIndex].envelope)
            lastDeliveredIndex += 1
        }
        if !delivered.isEmpty {
            onReplayEnvelopes?(delivered)
        }
    }

    private func payloadTRelMs(from envelope: AnyTelemetryEnvelope) -> Int? {
        switch envelope.payload {
        case .somatic(let p): return p.tRelMs
        case .symbolic(let p): return p.tRelMs
        case .noetic(let p): return p.tRelMs
        case .decision: return nil
        case .mpgDelta: return nil
        case .rogueVariable, .mufs: return nil
        case .unknown: return nil
        }
    }

    private func inferredTRelMs(from envelope: AnyTelemetryEnvelope) -> Int {
        if referenceDate == nil, let date = ISO8601DateFormatter().date(from: envelope.timestampUTC) {
            referenceDate = date
            return 0
        }
        if let ref = referenceDate, let date = ISO8601DateFormatter().date(from: envelope.timestampUTC) {
            return Int(date.timeIntervalSince(ref) * 1000)
        }
        return 0
    }
}

private struct ReplayFrame {
    let envelope: AnyTelemetryEnvelope
    let tRelMs: Int
}
