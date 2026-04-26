import SwiftUI

@main
struct GammaBreakApp: App {
    @StateObject private var settings = AppSettings()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(settings)
                .environmentObject(APIClient(settings: settings))
        }
    }
}
