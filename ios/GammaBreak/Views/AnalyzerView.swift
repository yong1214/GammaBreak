import SwiftUI

struct AnalyzerView: View {
    let symbol: String

    @EnvironmentObject var api: APIClient
    @State private var vm: AnalyzerViewModel?

    var body: some View {
        Group {
            if let vm {
                AnalyzerContent(vm: vm)
            } else {
                ProgressView()
            }
        }
        .navigationTitle(symbol)
        .task {
            if vm == nil {
                vm = AnalyzerViewModel(symbol: symbol, api: api)
                await vm?.refresh()
            }
        }
    }
}

private struct AnalyzerContent: View {
    @ObservedObject var vm: AnalyzerViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                headerCard
                predictionCard
                gammaCard
                chainCard
                if let err = vm.errorMessage {
                    Text(err).font(.caption).foregroundColor(.red).padding(.top)
                }
            }
            .padding()
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

    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                Text(vm.symbol).font(.largeTitle.bold())
                Spacer()
                if let spot = vm.chain?.underlyingPrice ?? vm.prediction?.spot {
                    Text(spot, format: .currency(code: "USD")).font(.title2.monospacedDigit())
                }
            }

            if let iv = vm.ivRank {
                HStack(spacing: 16) {
                    if let cur = iv.currentIv {
                        statBadge("IV", String(format: "%.1f%%", cur * 100), .blue)
                    }
                    if let rank = iv.rank {
                        statBadge("IV Rank", String(format: "%.0f", rank), rankColor(rank))
                    } else if let msg = iv.message {
                        Text(msg).font(.caption2).foregroundColor(.secondary).lineLimit(2)
                    }
                    if let pct = iv.percentile {
                        statBadge("IV %ile", String(format: "%.0f", pct), rankColor(pct))
                    }
                }
            }

            Picker("Horizon", selection: $vm.horizonMinutes) {
                Text("15m").tag(15)
                Text("1h").tag(60)
                Text("EOD").tag(390)
                Text("1D").tag(1440)
            }
            .pickerStyle(.segmented)
            .onChange(of: vm.horizonMinutes) { _, _ in Task { await vm.refresh() } }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
    }

    private func statBadge(_ label: String, _ value: String, _ color: Color) -> some View {
        VStack(spacing: 2) {
            Text(label).font(.caption2).foregroundColor(.secondary)
            Text(value).font(.subheadline.monospacedDigit().bold()).foregroundColor(color)
        }
    }

    private func rankColor(_ v: Double) -> Color {
        if v >= 70 { return .red }
        if v <= 30 { return .green }
        return .orange
    }

    @ViewBuilder
    private var predictionCard: some View {
        if let p = vm.prediction {
            PredictionCard(prediction: p)
        } else if vm.loading {
            ProgressView().frame(maxWidth: .infinity).padding()
        }
    }

    @ViewBuilder
    private var gammaCard: some View {
        if let g = vm.gamma { GammaCard(profile: g) }
    }

    @ViewBuilder
    private var chainCard: some View {
        if let chain = vm.chain { ChainCard(chain: chain) }
    }
}
