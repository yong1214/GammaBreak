import Foundation
import UserNotifications

/// Polls the backend for each watchlist symbol, compares spot to the gamma
/// walls, and fires a local notification when spot crosses (or comes within
/// the configured threshold of) a level. State is kept in UserDefaults so we
/// don't re-fire on every tick.
@MainActor
final class AlertService: ObservableObject {
    private let api: APIClient
    private let settings: AppSettings
    private var timer: Timer?

    init(api: APIClient, settings: AppSettings) {
        self.api = api
        self.settings = settings
    }

    func requestAuthorization() async -> Bool {
        do {
            return try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }

    func start() {
        stop()
        guard settings.alertsEnabled else { return }
        let interval = TimeInterval(max(1, settings.alertPollMinutes) * 60)
        timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            Task { @MainActor in await self?.tick() }
        }
        Task { await tick() }
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    func tick() async {
        guard settings.alertsEnabled else { return }
        for symbol in settings.watchlist {
            await checkSymbol(symbol)
        }
    }

    private func checkSymbol(_ symbol: String) async {
        guard let profile = try? await api.gammaProfile(symbol: symbol) else { return }
        guard let spot = profile.spot else { return }

        let thresholdPct = settings.alertThresholdPct / 100.0
        let levels: [(String, Double?)] = [
            ("Call wall", profile.callWall),
            ("Put wall", profile.putWall),
            ("Zero gamma", profile.zeroGamma),
        ]

        for (name, levelOpt) in levels {
            guard let level = levelOpt, level > 0 else { continue }
            let dist = abs(spot - level) / level
            if dist <= thresholdPct {
                let key = "alertFired-\(symbol)-\(name)-\(Int(level * 100))"
                let last = UserDefaults.standard.double(forKey: key)
                let now = Date().timeIntervalSince1970
                // Suppress duplicate alerts within an hour
                if now - last > 3600 {
                    UserDefaults.standard.set(now, forKey: key)
                    fire(symbol: symbol, level: name, levelPrice: level, spot: spot)
                }
            }
        }
    }

    private func fire(symbol: String, level: String, levelPrice: Double, spot: Double) {
        let content = UNMutableNotificationContent()
        content.title = "\(symbol): near \(level)"
        content.body = String(format: "Spot %.2f, %@ at %.2f (Δ %+.2f%%)",
                              spot, level, levelPrice, (spot - levelPrice) / levelPrice * 100)
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil
        )
        UNUserNotificationCenter.current().add(request)
    }
}
