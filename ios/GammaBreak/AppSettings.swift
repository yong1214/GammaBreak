import Foundation
import Combine

final class AppSettings: ObservableObject {
    @Published var backendURL: String {
        didSet { UserDefaults.standard.set(backendURL, forKey: "backendURL") }
    }

    @Published var authToken: String {
        didSet { UserDefaults.standard.set(authToken, forKey: "authToken") }
    }

    @Published var watchlist: [String] {
        didSet { UserDefaults.standard.set(watchlist, forKey: "watchlist") }
    }

    init() {
        let defaults = UserDefaults.standard
        self.backendURL = defaults.string(forKey: "backendURL") ?? "http://localhost:8000"
        self.authToken = defaults.string(forKey: "authToken") ?? ""
        self.watchlist = defaults.stringArray(forKey: "watchlist") ?? ["SPY", "QQQ", "AAPL", "NVDA", "TSLA"]
    }
}
