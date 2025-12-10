//
//  ImmersiveView.swift
//  Laiza
//
//  Created by Johan Sellström on 2025-11-27.
//

import SwiftUI
import H3LIXUI
import H3LIXState

struct ImmersiveView: View {

    @ObservedObject var store: H3LIXStore
    @ObservedObject var playback: H3LIXPlaybackController
    @ObservedObject var interaction: H3LIXInteractionModel
    @ObservedObject var teaching: TeachingStore

    var body: some View {
        // Reuse the full RealityKit immersive view from H3LIXUI so the simulator shows content.
        H3LIXImmersiveView(
            store: store,
            playback: playback,
            interaction: interaction,
            teaching: teaching
        )
    }
}

#if DEBUG
struct ImmersiveView_Previews: PreviewProvider {
    static var previews: some View {
        Text("Immersive view preview unavailable without RealityKit scene.")
    }
}
#endif
