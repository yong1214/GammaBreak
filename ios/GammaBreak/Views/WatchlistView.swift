import SwiftUI

struct WatchlistView: View {
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var api: APIClient
    @State private var newSymbol: String = ""

    var body: some View {
        List {
            Section {
                HStack {
                    TextField("Add symbol (e.g. SPY)", text: $newSymbol)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                    Button {
                        let sym = newSymbol.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
                        guard !sym.isEmpty, !settings.watchlist.contains(sym) else { return }
                        settings.watchlist.append(sym)
                        newSymbol = ""
                    } label: { Image(systemName: "plus.circle.fill") }
                }
            }
            Section("Tickers") {
                ForEach(settings.watchlist, id: \.self) { sym in
                    NavigationLink(value: sym) {
                        HStack {
                            Text(sym).font(.headline)
                            Spacer()
                            Image(systemName: "chevron.right").foregroundColor(.secondary)
                        }
                    }
                }
                .onDelete { idx in settings.watchlist.remove(atOffsets: idx) }
            }
        }
        .navigationTitle("GammaBreak")
        .navigationDestination(for: String.self) { sym in
            AnalyzerView(symbol: sym)
        }
    }
}
