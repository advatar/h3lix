import UIKit
import SwiftUI

#if canImport(ComposeApp)
import ComposeApp

struct ComposeView: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController {
        MainViewControllerKt.MainViewController()
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {}
}

struct ContentView: View {
    var body: some View {
        ComposeView()
            .ignoresSafeArea()
    }
}
#else
struct ContentView: View {
    var body: some View {
        VStack(spacing: 12) {
            Text("ComposeApp framework not found")
                .font(.headline)
            Text("Run Gradle iOS framework task and re-open Xcode.")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .padding()
    }
}
#endif


