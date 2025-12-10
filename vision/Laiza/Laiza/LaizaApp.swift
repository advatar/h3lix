//
//  LaizaApp.swift
//  Laiza
//
//  Created by Johan Sellström on 2025-11-27.
//

import SwiftUI
import H3LIXNet
import H3LIXState

@main
struct LaizaApp: App {

    @State private var appModel = AppModel()
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
            ContentView(
                store: store,
                playback: playback,
                interaction: interaction,
                teaching: teaching,
                immersiveSpaceIsShown: $immersiveSpaceIsShown
            )
                .environment(appModel)
        }

        ImmersiveSpace(id: appModel.immersiveSpaceID) {
            ImmersiveView(
                store: store,
                playback: playback,
                interaction: interaction,
                teaching: teaching
            )
                .environment(appModel)
                .onAppear {
                    appModel.immersiveSpaceState = .open
                    immersiveSpaceIsShown = true
                }
                .onDisappear {
                    appModel.immersiveSpaceState = .closed
                    immersiveSpaceIsShown = false
                }
        }
        .immersionStyle(selection: .constant(.full), in: .full)
    }
}
