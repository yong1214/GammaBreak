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
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text(vm.symbol).font(.largeTitle.bold())
                Spacer()
                if let spot = vm.chain?.underlyingPrice ?? vm.prediction?.spot {
                    Text(spot, format: .currency(code: "USD")).font(.title2.monospacedDigit())
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
