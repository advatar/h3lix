#if os(visionOS)
import SwiftUI
import H3LIXCore

struct TeachingOverlay: View {
    let step: LessonStep
    let onPrev: () -> Void
    let onNext: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(step.title).font(.headline)
            Text(step.descriptionMd)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(6)
            HStack {
                Button("Prev", action: onPrev).buttonStyle(.bordered)
                Button("Next", action: onNext).buttonStyle(.borderedProminent)
            }
        }
        .padding(12)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}
#endif
