import XCTest
@testable import H3LIXState
@testable import H3LIXCore
@testable import H3LIXNet

@MainActor
final class TeachingStoreTests: XCTestCase {
    func testLessonDecoding() throws {
        let json = """
        {
          "lesson_id": "lesson_intro",
          "title": "Intro to H3LIX",
          "description_md": "Basics of somatic/symbolic/noetic.",
          "difficulty": "intro",
          "target_audience": "student",
          "backing_data": { "kind": "synthetic", "scenario_id": "toy" },
          "modules": [
            {
              "module_id": "m1",
              "title": "Module 1",
              "description_md": "desc",
              "order": 1,
              "steps": [
                {
                  "step_id": "s1",
                  "title": "Step 1",
                  "description_md": "step desc",
                  "scene_control_delta": { "focus_node_id": "n1", "t_rel_ms": 100, "mode": "live" },
                  "camera_hint": { "position": [0,1,0], "look_at": [0,0,0] },
                  "interaction_task": { "kind": "select_node", "target_node_id": "n1" },
                  "quiz": { "kind": "true_false", "statement": "Is H3LIX layered?", "answer": true },
                  "estimated_seconds": 30
                }
              ]
            }
          ]
        }
        """
        let data = Data(json.utf8)
        let lesson = try JSONDecoder().decode(Lesson.self, from: data)
        XCTAssertEqual(lesson.id, "lesson_intro")
        XCTAssertEqual(lesson.modules.count, 1)
        XCTAssertEqual(lesson.modules.first?.steps.first?.sceneControlDelta?.tRelMs, 100)
    }

    func testTeachingStoreProgression() async {
        let client = H3LIXClient(configuration: .init(baseURL: URL(string: "http://localhost")!))
        let store = TeachingStore(client: client)

        let step = LessonStep(
            id: "s1",
            title: "Step",
            descriptionMd: "desc",
            sceneControlDelta: nil,
            cameraHint: nil,
            interactionTask: nil,
            quiz: nil,
            estimatedSeconds: nil
        )
        let module = LessonModule(id: "m1", title: "m", descriptionMd: "d", order: 1, steps: [step, step])
        let lesson = Lesson(id: "l1", title: "Lesson", descriptionMd: "d", difficulty: "intro", targetAudience: "student", modules: [module], backingData: .synthetic(scenarioID: "toy"))
        store.setLessonForTesting(lesson)

        XCTAssertEqual(store.currentStepIndex, 0)
        store.nextStep()
        XCTAssertEqual(store.currentStepIndex, 1)
        store.nextStep() // should mark complete
        XCTAssertEqual(store.progress?.completed, true)
        store.previousStep()
        XCTAssertEqual(store.currentStepIndex, 0)
    }
}
