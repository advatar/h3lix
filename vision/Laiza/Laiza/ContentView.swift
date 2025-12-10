//
//  ContentView.swift
//  Laiza
//
//  Created by Johan Sellström on 2025-11-27.
//

import SwiftUI
import H3LIXUI
import H3LIXState

struct ContentView: View {

    @ObservedObject var store: H3LIXStore
    @ObservedObject var playback: H3LIXPlaybackController
    @ObservedObject var interaction: H3LIXInteractionModel
    @ObservedObject var teaching: TeachingStore
    @Binding var immersiveSpaceIsShown: Bool

    var body: some View {
        DashboardView(
            store: store,
            playback: playback,
            interaction: interaction,
            teaching: teaching,
            immersiveSpaceIsShown: $immersiveSpaceIsShown,
            immersiveSpaceID: "ImmersiveSpace"
        )
    }
}

#if DEBUG
struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        Text("Preview unavailable without H3LIXScene/UI targets.")
    }
}
#endif
