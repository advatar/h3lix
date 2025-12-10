import Foundation
import Combine
import H3LIXCore
import H3LIXNet

@MainActor
public final class TeachingStore: ObservableObject {
    @Published public private(set) var lessons: [Lesson] = []
    @Published public private(set) var activeLesson: Lesson?
    @Published public private(set) var progress: LessonProgress?
    @Published public private(set) var currentModuleIndex: Int = 0
    @Published public private(set) var currentStepIndex: Int = 0
    @Published public private(set) var statusMessage: String?

    private let client: H3LIXClient
    private let userID: String

    public init(client: H3LIXClient, userID: String = "local-user") {
        self.client = client
        self.userID = userID
    }

    public func refreshLessons() {
        Task { @MainActor in
            do {
                lessons = try await client.listLessons()
            } catch {
                lessons = []
                statusMessage = "Failed to load lessons: \(error)"
            }
        }
    }

    public func loadLesson(id: String) {
        Task { @MainActor in
            do {
                let lesson = try await client.fetchLesson(id: id)
                activeLesson = lesson
                let serverProgress = try? await client.fetchLessonProgress(lessonID: id, userID: userID)
                progress = serverProgress ?? LessonProgress(userID: userID, lessonID: id, currentModuleIdx: 0, currentStepIdx: 0, completed: false)
                currentModuleIndex = progress?.currentModuleIdx ?? 0
                currentStepIndex = progress?.currentStepIdx ?? 0
            } catch {
                statusMessage = "Failed to load lesson: \(error)"
            }
        }
    }

    public func nextStep() {
        guard var progress = progress, let lesson = activeLesson else { return }
        let module = lesson.modules[safe: progress.currentModuleIdx]
        if let module, progress.currentStepIdx + 1 < module.steps.count {
            progress.currentStepIdx += 1
        } else if progress.currentModuleIdx + 1 < lesson.modules.count {
            progress.currentModuleIdx += 1
            progress.currentStepIdx = 0
        } else {
            progress.completed = true
        }
        apply(progress: progress)
    }

    public func previousStep() {
        guard var progress = progress, let lesson = activeLesson else { return }
        if progress.currentStepIdx > 0 {
            progress.currentStepIdx -= 1
        } else if progress.currentModuleIdx > 0 {
            progress.currentModuleIdx -= 1
            progress.currentStepIdx = lesson.modules[progress.currentModuleIdx].steps.count - 1
        }
        apply(progress: progress)
    }

    public func markCompleted() {
        guard var progress = progress else { return }
        progress.completed = true
        apply(progress: progress)
    }

    private func apply(progress: LessonProgress) {
        self.progress = progress
        self.currentModuleIndex = progress.currentModuleIdx
        self.currentStepIndex = progress.currentStepIdx
        Task { @MainActor in
            do {
                try await client.updateLessonProgress(progress)
            } catch {
                statusMessage = "Failed to save progress: \(error)"
            }
        }
    }

    public var currentStep: LessonStep? {
        guard let lesson = activeLesson else { return nil }
        return lesson.modules[safe: currentModuleIndex]?.steps[safe: currentStepIndex]
    }

    // MARK: - Testing helpers

    public func setLessonForTesting(_ lesson: Lesson) {
        activeLesson = lesson
        let progress = LessonProgress(userID: userID, lessonID: lesson.id, currentModuleIdx: 0, currentStepIdx: 0, completed: false)
        self.progress = progress
        currentModuleIndex = 0
        currentStepIndex = 0
    }
}

private extension Collection {
    subscript(safe index: Index) -> Element? {
        guard indices.contains(index) else { return nil }
        return self[index]
    }
}
