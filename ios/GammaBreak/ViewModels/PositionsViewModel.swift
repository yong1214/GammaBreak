import Foundation
import SwiftUI

@MainActor
final class PositionsViewModel: ObservableObject {
    @Published private(set) var positions: [Position] = []
    @Published private(set) var account: AccountSummary?
    @Published private(set) var loading = false
    @Published var errorMessage: String?

    private let api: APIClient

    init(api: APIClient) {
        self.api = api
    }

    func refresh() async {
        loading = true
        defer { loading = false }
        errorMessage = nil

        async let posTask: () = fetchPositions()
        async let accTask: () = fetchAccount()
        _ = await (posTask, accTask)
    }

    private func fetchPositions() async {
        do { positions = try await api.positions() }
        catch { errorMessage = error.localizedDescription }
    }

    private func fetchAccount() async {
        do { account = try await api.account() }
        catch { /* swallow — account summary is best-effort */ }
    }
}
