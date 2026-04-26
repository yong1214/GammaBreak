import SwiftUI

struct ChainCard: View {
    let chain: OptionChain

    private var rows: [ChainRow] {
        let grouped = Dictionary(grouping: chain.quotes, by: { $0.strike })
        return grouped.keys.sorted().map { strike in
            let calls = grouped[strike]?.first(where: { $0.right == .call })
            let puts = grouped[strike]?.first(where: { $0.right == .put })
            return ChainRow(strike: strike, call: calls, put: puts)
        }
    }

    private var atmIndex: Int? {
        guard let spot = chain.underlyingPrice else { return nil }
        return rows.enumerated().min(by: { abs($0.element.strike - spot) < abs($1.element.strike - spot) })?.offset
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Chain · \(chain.symbol)").font(.headline)

            HStack {
                Text("Δ / Γ").frame(maxWidth: .infinity, alignment: .leading)
                Text("Strike").frame(width: 70)
                Text("Δ / Γ").frame(maxWidth: .infinity, alignment: .trailing)
            }
            .font(.caption2)
            .foregroundColor(.secondary)

            ForEach(Array(rows.enumerated()), id: \.element.strike) { idx, row in
                HStack(alignment: .center) {
                    callCell(row.call)
                    strikeCell(row.strike, isATM: idx == atmIndex)
                    putCell(row.put)
                }
                .font(.caption.monospacedDigit())
                .padding(.vertical, 2)
                if idx == atmIndex {
                    Divider()
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
    }

    @ViewBuilder
    private func callCell(_ q: OptionQuote?) -> some View {
        if let q {
            HStack {
                Text(formatGreek(q.greeks.delta))
                    .foregroundColor(.green)
                Text(formatGreek(q.greeks.gamma, scale: 1000))
                    .foregroundColor(.secondary)
                Spacer()
            }.frame(maxWidth: .infinity, alignment: .leading)
        } else {
            Text("—").frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    @ViewBuilder
    private func putCell(_ q: OptionQuote?) -> some View {
        if let q {
            HStack {
                Spacer()
                Text(formatGreek(q.greeks.gamma, scale: 1000))
                    .foregroundColor(.secondary)
                Text(formatGreek(q.greeks.delta))
                    .foregroundColor(.red)
            }.frame(maxWidth: .infinity, alignment: .trailing)
        } else {
            Text("—").frame(maxWidth: .infinity, alignment: .trailing)
        }
    }

    private func strikeCell(_ strike: Double, isATM: Bool) -> some View {
        Text(strike, format: .number.precision(.fractionLength(0...2)))
            .frame(width: 70)
            .padding(.vertical, 2)
            .background(isATM ? Color.accentColor.opacity(0.18) : .clear)
            .cornerRadius(4)
            .fontWeight(isATM ? .bold : .regular)
    }

    private func formatGreek(_ v: Double?, scale: Double = 1) -> String {
        guard let v else { return "—" }
        return String(format: "%.2f", v * scale)
    }
}

private struct ChainRow {
    let strike: Double
    let call: OptionQuote?
    let put: OptionQuote?
}
