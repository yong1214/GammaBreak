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

    @Published var alertsEnabled: Bool {
        didSet { UserDefaults.standard.set(alertsEnabled, forKey: "alertsEnabled") }
    }

    @Published var alertThresholdPct: Double {
        didSet { UserDefaults.standard.set(alertThresholdPct, forKey: "alertThresholdPct") }
    }

    @Published var alertPollMinutes: Int {
        didSet { UserDefaults.standard.set(alertPollMinutes, forKey: "alertPollMinutes") }
    }

    init() {
        let defaults = UserDefaults.standard
        self.backendURL = defaults.string(forKey: "backendURL") ?? "http://localhost:8000"
        self.authToken = defaults.string(forKey: "authToken") ?? ""
        self.watchlist = defaults.stringArray(forKey: "watchlist") ?? ["SPY", "QQQ", "AAPL", "NVDA", "TSLA"]
        self.alertsEnabled = defaults.object(forKey: "alertsEnabled") as? Bool ?? false
        self.alertThresholdPct = defaults.object(forKey: "alertThresholdPct") as? Double ?? 0.25
        self.alertPollMinutes = defaults.object(forKey: "alertPollMinutes") as? Int ?? 5
    }
}
