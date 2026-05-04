import SwiftUI

struct PositionsView: View {
    @EnvironmentObject var api: APIClient
    @State private var vm: PositionsViewModel?

    var body: some View {
        Group {
            if let vm {
                PositionsContent(vm: vm)
            } else {
                ProgressView()
            }
        }
        .navigationTitle("Positions")
        .task {
            if vm == nil {
                vm = PositionsViewModel(api: api)
                await vm?.refresh()
            }
        }
    }
}

private struct PositionsContent: View {
    @ObservedObject var vm: PositionsViewModel

    var body: some View {
        List {
            if let acct = vm.account {
                Section("Account") {
                    accountRow("Net Liq", acct.netLiquidation)
                    accountRow("Buying Power", acct.buyingPower)
                    accountRow("Available", acct.availableFunds)
                    accountRow("Maint Margin", acct.maintMarginReq)
                }
            }

            Section("Positions") {
                if vm.positions.isEmpty && !vm.loading {
                    Text("No open positions")
                        .foregroundColor(.secondary)
                        .font(.subheadline)
                }
                ForEach(vm.positions) { p in
                    PositionRow(position: p)
                }
            }

            if let err = vm.errorMessage {
                Section {
                    Text(err).font(.caption).foregroundColor(.red)
                }
            }
        }
        .toolbar {
            ToolbarItem {
                Button { Task { await vm.refresh() } } label: {
                    if vm.loading { ProgressView() } else { Image(systemName: "arrow.clockwise") }
                }
            }
        }
        .refreshable { await vm.refresh() }
    }

    private func accountRow(_ label: String, _ value: Double?) -> some View {
        HStack {
            Text(label).font(.subheadline)
            Spacer()
            if let value {
                Text(value, format: .currency(code: "USD"))
                    .font(.subheadline.monospacedDigit())
            } else {
                Text("—").foregroundColor(.secondary)
            }
        }
    }
}

private struct PositionRow: View {
    let position: Position

    private var displayTitle: String {
        if position.secType == "OPT", let exp = position.expiry, let strike = position.strike, let right = position.right {
            return "\(position.symbol)  \(exp.suffix(6))  \(Int(strike))\(right)"
        }
        return "\(position.symbol)  \(position.secType)"
    }

    private var pnlColor: Color {
        guard let p = position.unrealizedPnl else { return .secondary }
        return p >= 0 ? .green : .red
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(displayTitle).font(.subheadline.weight(.semibold))
                Spacer()
                Text("\(Int(position.position))")
                    .font(.subheadline.monospacedDigit())
                    .foregroundColor(position.position >= 0 ? .primary : .red)
            }
            HStack {
                Text("avg \(position.avgCost, format: .number.precision(.fractionLength(2)))")
                    .font(.caption.monospacedDigit())
                    .foregroundColor(.secondary)
                if let mp = position.marketPrice {
                    Text("→ \(mp, format: .number.precision(.fractionLength(2)))")
                        .font(.caption.monospacedDigit())
                        .foregroundColor(.secondary)
                }
                Spacer()
                if let pnl = position.unrealizedPnl {
                    Text(pnl, format: .currency(code: "USD"))
                        .font(.caption.monospacedDigit())
                        .foregroundColor(pnlColor)
                }
            }
        }
        .padding(.vertical, 2)
    }
}
