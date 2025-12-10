import Foundation

public struct Lesson: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let descriptionMd: String
    public let difficulty: String
    public let targetAudience: String
    public let modules: [LessonModule]
    public let backingData: LessonDataSource

    enum CodingKeys: String, CodingKey {
        case id = "lesson_id"
        case title
        case descriptionMd = "description_md"
        case difficulty
        case targetAudience = "target_audience"
        case modules
        case backingData = "backing_data"
    }
}

public struct LessonModule: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let descriptionMd: String
    public let order: Int
    public let steps: [LessonStep]

    enum CodingKeys: String, CodingKey {
        case id = "module_id"
        case title
        case descriptionMd = "description_md"
        case order
        case steps
    }
}

public struct LessonStep: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let descriptionMd: String
    public let sceneControlDelta: SceneControlDelta?
    public let cameraHint: CameraHint?
    public let interactionTask: InteractionTaskSpec?
    public let quiz: QuizSpec?
    public let estimatedSeconds: Int?

    enum CodingKeys: String, CodingKey {
        case id = "step_id"
        case title
        case descriptionMd = "description_md"
        case sceneControlDelta = "scene_control_delta"
        case cameraHint = "camera_hint"
        case interactionTask = "interaction_task"
        case quiz
        case estimatedSeconds = "estimated_seconds"
    }
}

public struct SceneControlDelta: Codable, Hashable, Sendable {
    public let focusNodeID: String?
    public let tRelMs: Int?
    public let mode: String?
}

public struct CameraHint: Codable, Hashable, Sendable {
    public let position: [Double]?
    public let lookAt: [Double]?
}

public enum LessonDataSource: Codable, Hashable, Sendable {
    case synthetic(scenarioID: String)
    case recorded(sessionID: String, window: [Int])
    case cohort(cohortID: String)

    enum CodingKeys: String, CodingKey {
        case kind
        case scenarioID = "scenario_id"
        case sessionID = "session_id"
        case windowMs = "window_ms"
        case cohortID = "cohort_id"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let kind = try container.decode(String.self, forKey: .kind)
        switch kind {
        case "synthetic":
            let id = try container.decode(String.self, forKey: .scenarioID)
            self = .synthetic(scenarioID: id)
        case "recorded_session":
            let id = try container.decode(String.self, forKey: .sessionID)
            let window = try container.decode([Int].self, forKey: .windowMs)
            self = .recorded(sessionID: id, window: window)
        case "cohort":
            let id = try container.decode(String.self, forKey: .cohortID)
            self = .cohort(cohortID: id)
        default:
            self = .synthetic(scenarioID: "unknown")
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .synthetic(let scenarioID):
            try container.encode("synthetic", forKey: .kind)
            try container.encode(scenarioID, forKey: .scenarioID)
        case .recorded(let sessionID, let window):
            try container.encode("recorded_session", forKey: .kind)
            try container.encode(sessionID, forKey: .sessionID)
            try container.encode(window, forKey: .windowMs)
        case .cohort(let cohortID):
            try container.encode("cohort", forKey: .kind)
            try container.encode(cohortID, forKey: .cohortID)
        }
    }
}

public enum InteractionTaskSpec: Codable, Hashable, Sendable {
    case selectNode(targetNodeID: String)
    case selectRogue(rogueID: String)
    case scrubTime(from: Int, to: Int)
    case toggleMufs(decisionID: String)

    enum CodingKeys: String, CodingKey {
        case kind
        case targetNodeID = "target_node_id"
        case rogueID = "target_rogue_id"
        case from
        case to
        case decisionID = "decision_id"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let kind = try container.decode(String.self, forKey: .kind)
        switch kind {
        case "select_node":
            let id = try container.decode(String.self, forKey: .targetNodeID)
            self = .selectNode(targetNodeID: id)
        case "select_rv":
            let id = try container.decode(String.self, forKey: .rogueID)
            self = .selectRogue(rogueID: id)
        case "scrub_time":
            let from = try container.decode(Int.self, forKey: .from)
            let to = try container.decode(Int.self, forKey: .to)
            self = .scrubTime(from: from, to: to)
        case "toggle_mufs":
            let id = try container.decode(String.self, forKey: .decisionID)
            self = .toggleMufs(decisionID: id)
        default:
            self = .selectNode(targetNodeID: "")
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .selectNode(let id):
            try container.encode("select_node", forKey: .kind)
            try container.encode(id, forKey: .targetNodeID)
        case .selectRogue(let id):
            try container.encode("select_rv", forKey: .kind)
            try container.encode(id, forKey: .rogueID)
        case .scrubTime(let from, let to):
            try container.encode("scrub_time", forKey: .kind)
            try container.encode(from, forKey: .from)
            try container.encode(to, forKey: .to)
        case .toggleMufs(let id):
            try container.encode("toggle_mufs", forKey: .kind)
            try container.encode(id, forKey: .decisionID)
        }
    }
}

public enum QuizSpec: Codable, Hashable, Sendable {
    case mcq(question: String, options: [String], correctIndex: Int)
    case trueFalse(statement: String, answer: Bool)
    case hotspot(question: String, targetNodeID: String)

    enum CodingKeys: String, CodingKey {
        case kind
        case question
        case options
        case correctIndex = "correct_index"
        case statement
        case answer
        case targetNodeID = "target_node_id"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let kind = try container.decode(String.self, forKey: .kind)
        switch kind {
        case "mcq":
            let q = try container.decode(String.self, forKey: .question)
            let opts = try container.decode([String].self, forKey: .options)
            let idx = try container.decode(Int.self, forKey: .correctIndex)
            self = .mcq(question: q, options: opts, correctIndex: idx)
        case "true_false":
            let stmt = try container.decode(String.self, forKey: .statement)
            let ans = try container.decode(Bool.self, forKey: .answer)
            self = .trueFalse(statement: stmt, answer: ans)
        case "hotspot":
            let q = try container.decode(String.self, forKey: .question)
            let id = try container.decode(String.self, forKey: .targetNodeID)
            self = .hotspot(question: q, targetNodeID: id)
        default:
            self = .trueFalse(statement: "", answer: true)
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .mcq(let question, let options, let idx):
            try container.encode("mcq", forKey: .kind)
            try container.encode(question, forKey: .question)
            try container.encode(options, forKey: .options)
            try container.encode(idx, forKey: .correctIndex)
        case .trueFalse(let statement, let answer):
            try container.encode("true_false", forKey: .kind)
            try container.encode(statement, forKey: .statement)
            try container.encode(answer, forKey: .answer)
        case .hotspot(let question, let targetNodeID):
            try container.encode("hotspot", forKey: .kind)
            try container.encode(question, forKey: .question)
            try container.encode(targetNodeID, forKey: .targetNodeID)
        }
    }
}

public struct LessonProgress: Codable, Hashable, Sendable {
    public let userID: String
    public let lessonID: String
    public var currentModuleIdx: Int
    public var currentStepIdx: Int
    public var completed: Bool

    public init(
        userID: String,
        lessonID: String,
        currentModuleIdx: Int,
        currentStepIdx: Int,
        completed: Bool
    ) {
        self.userID = userID
        self.lessonID = lessonID
        self.currentModuleIdx = currentModuleIdx
        self.currentStepIdx = currentStepIdx
        self.completed = completed
    }

    enum CodingKeys: String, CodingKey {
        case userID = "user_id"
        case lessonID = "lesson_id"
        case currentModuleIdx = "current_module_idx"
        case currentStepIdx = "current_step_idx"
        case completed
    }
}
