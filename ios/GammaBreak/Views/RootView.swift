import SwiftUI

struct RootView: View {
    var body: some View {
        TabView {
            NavigationStack { WatchlistView() }
                .tabItem { Label("Watchlist", systemImage: "list.star") }
            NavigationStack { SettingsView() }
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
    }
}
