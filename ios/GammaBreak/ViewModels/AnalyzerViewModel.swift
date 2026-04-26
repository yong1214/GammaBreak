import Foundation
import SwiftUI

@MainActor
final class AnalyzerViewModel: ObservableObject {
    @Published var symbol: String
    @Published var horizonMinutes: Int = 60

    @Published private(set) var chain: OptionChain?
    @Published private(set) var gamma: GammaProfile?
    @Published private(set) var prediction: PricePrediction?
    @Published private(set) var loading = false
    @Published var errorMessage: String?

    private let api: APIClient

    init(symbol: String, api: APIClient) {
        self.symbol = symbol.uppercased()
        self.api = api
    }

    func refresh() async {
        loading = true
        defer { loading = false }
        errorMessage = nil

        async let chainTask = safeFetch { try await self.api.optionChain(symbol: self.symbol) }
        async let gammaTask = safeFetch { try await self.api.gammaProfile(symbol: self.symbol) }
        async let predictTask = safeFetch {
            try await self.api.predict(symbol: self.symbol, horizonMinutes: self.horizonMinutes)
        }

        chain = await chainTask
        gamma = await gammaTask
        prediction = await predictTask
    }

    private func safeFetch<T>(_ op: @escaping () async throws -> T) async -> T? {
        do {
            return try await op()
        } catch {
            // surface only the first error so the UI isn't spammed
            if errorMessage == nil { errorMessage = error.localizedDescription }
            return nil
        }
    }
}
