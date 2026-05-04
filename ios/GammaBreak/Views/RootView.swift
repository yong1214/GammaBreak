import SwiftUI

struct RootView: View {
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var alerts: AlertService

    var body: some View {
        TabView {
            NavigationStack { WatchlistView() }
                .tabItem { Label("Watchlist", systemImage: "list.star") }
            NavigationStack { PositionsView() }
                .tabItem { Label("Positions", systemImage: "briefcase") }
            NavigationStack { SettingsView() }
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
        .task {
            if settings.alertsEnabled {
                _ = await alerts.requestAuthorization()
                alerts.start()
            }
        }
        .onChange(of: settings.alertsEnabled) { _, enabled in
            if enabled {
                Task {
                    _ = await alerts.requestAuthorization()
                    alerts.start()
                }
            } else {
                alerts.stop()
            }
        }
    }
}
