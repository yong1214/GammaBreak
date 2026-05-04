import SwiftUI

@main
struct GammaBreakApp: App {
    @StateObject private var settings: AppSettings
    @StateObject private var api: APIClient
    @StateObject private var alerts: AlertService

    init() {
        let s = AppSettings()
        let a = APIClient(settings: s)
        _settings = StateObject(wrappedValue: s)
        _api = StateObject(wrappedValue: a)
        _alerts = StateObject(wrappedValue: AlertService(api: a, settings: s))
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(settings)
                .environmentObject(api)
                .environmentObject(alerts)
        }
    }
}
