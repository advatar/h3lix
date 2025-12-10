// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "H3LIXVision",
    platforms: [
        .visionOS(.v26), .macOS(.v26)
    ],
    products: [
        .library(name: "H3LIXCore", targets: ["H3LIXCore"]),
        .library(name: "H3LIXNet", targets: ["H3LIXNet"]),
        .library(name: "H3LIXState", targets: ["H3LIXState"]),
        .library(name: "H3LIXVisualState", targets: ["H3LIXVisualState"]),
        .library(name: "H3LIXScene", targets: ["H3LIXScene"]),
        .library(name: "H3LIXUI", targets: ["H3LIXUI"])
    ],
    targets: [
        .target(
            name: "SymbiosisCore",
            dependencies: []
        ),
        .target(
            name: "H3LIXCore",
            dependencies: []
        ),
        .target(
            name: "H3LIXNet",
            dependencies: ["H3LIXCore"],
            linkerSettings: [
                .linkedFramework("HealthKit", .when(platforms: [.visionOS]))
            ]
        ),
        .target(
            name: "H3LIXState",
            dependencies: ["H3LIXCore", "H3LIXNet", "SymbiosisCore"]
        ),
        .target(
            name: "H3LIXVisualState",
            dependencies: ["H3LIXCore", "H3LIXState"]
        ),
        .target(
            name: "H3LIXScene",
            dependencies: ["H3LIXCore", "H3LIXState", "H3LIXVisualState"]
        ),
        .target(
            name: "H3LIXUI",
            dependencies: ["H3LIXCore", "H3LIXState", "H3LIXVisualState", "H3LIXScene"]
        ),
        .executableTarget(
            name: "H3LIXVision",
            dependencies: ["H3LIXCore", "H3LIXNet", "H3LIXState", "H3LIXVisualState", "H3LIXScene", "H3LIXUI"]
        ),
        .testTarget(
            name: "H3LIXVisualStateTests",
            dependencies: ["H3LIXVisualState", "H3LIXState", "H3LIXCore"]
        ),
        .testTarget(
            name: "H3LIXTeachingTests",
            dependencies: ["H3LIXState", "H3LIXCore"]
        )
    ]
)
