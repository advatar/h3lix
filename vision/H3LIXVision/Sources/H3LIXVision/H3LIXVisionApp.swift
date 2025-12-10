import SwiftUI
import H3LIXUI
import H3LIXState
import H3LIXNet

#if os(visionOS)
@main
struct H3LIXVisionApp: App {
    private let immersiveSpaceID = "ImmersiveSpace"
    @StateObject private var store: H3LIXStore
    @StateObject private var playback = H3LIXPlaybackController()
    @StateObject private var interaction = H3LIXInteractionModel()
    @StateObject private var teaching: TeachingStore
    @State private var immersiveSpaceIsShown = false

    init() {
        let baseURLString = ProcessInfo.processInfo.environment["H3LIX_BASE_URL"] ?? "http://localhost:8000"
        let url = URL(string: baseURLString) ?? URL(string: "http://localhost:8000")!
        let client = H3LIXClient(configuration: .init(baseURL: url))
        _store = StateObject(wrappedValue: H3LIXStore(client: client))
        _teaching = StateObject(wrappedValue: TeachingStore(client: client))
    }

    var body: some Scene {
        WindowGroup {
            DashboardView(
                store: store,
                playback: playback,
                interaction: interaction,
                teaching: teaching,
                immersiveSpaceIsShown: $immersiveSpaceIsShown,
                immersiveSpaceID: immersiveSpaceID
            )
        }

        ImmersiveSpace(id: immersiveSpaceID) {
            let _ = print("[H3LIX] ImmersiveSpace content builder")
            H3LIXImmersiveView(store: store, playback: playback, interaction: interaction, teaching: teaching)
        }
        .immersionStyle(selection: .constant(.full), in: .full)
    }
}
#elseif os(macOS)
@main
struct H3LIXVisionApp: App {
    @StateObject private var store: H3LIXStore
    @StateObject private var playback = H3LIXPlaybackController()
    @StateObject private var interaction = H3LIXInteractionModel()
    @StateObject private var teaching: TeachingStore
    @State private var immersiveSpaceIsShown = false

    init() {
        let baseURLString = ProcessInfo.processInfo.environment["H3LIX_BASE_URL"] ?? "http://localhost:8000"
        let url = URL(string: baseURLString) ?? URL(string: "http://localhost:8000")!
        let client = H3LIXClient(configuration: .init(baseURL: url))
        _store = StateObject(wrappedValue: H3LIXStore(client: client))
        _teaching = StateObject(wrappedValue: TeachingStore(client: client))
    }

    var body: some Scene {
        WindowGroup {
            DashboardView(
                store: store,
                playback: playback,
                interaction: interaction,
                teaching: teaching,
                immersiveSpaceIsShown: $immersiveSpaceIsShown
            )
        }
    }
}
#endif
