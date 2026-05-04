import SwiftUI

struct OrderTicketView: View {
    let quote: OptionQuote
    @EnvironmentObject var api: APIClient
    @Environment(\.dismiss) private var dismiss

    @State private var action: String = "BUY"
    @State private var quantity: Int = 1
    @State private var orderType: String = "LMT"
    @State private var limitPrice: Double = 0
    @State private var submitting = false
    @State private var resultMessage: String?
    @State private var resultIsError = false

    private static let dateFmt: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f
    }()

    var body: some View {
        NavigationStack {
            Form {
                Section("Contract") {
                    LabeledContent("Symbol", value: quote.symbol)
                    LabeledContent("Expiry", value: Self.dateFmt.string(from: quote.expiry))
                    LabeledContent("Strike") {
                        Text(quote.strike, format: .number.precision(.fractionLength(2)))
                    }
                    LabeledContent("Right", value: quote.right == .call ? "Call" : "Put")
                    if let bid = quote.bid, let ask = quote.ask {
                        LabeledContent("Bid / Ask") {
                            Text(String(format: "%.2f / %.2f", bid, ask))
                                .font(.subheadline.monospacedDigit())
                        }
                    }
                }

                Section("Order") {
                    Picker("Action", selection: $action) {
                        Text("Buy").tag("BUY")
                        Text("Sell").tag("SELL")
                    }
                    .pickerStyle(.segmented)

                    Stepper("Quantity: \(quantity)", value: $quantity, in: 1...100)

                    Picker("Type", selection: $orderType) {
                        Text("Limit").tag("LMT")
                        Text("Market").tag("MKT")
                    }
                    .pickerStyle(.segmented)

                    if orderType == "LMT" {
                        HStack {
                            Text("Limit price")
                            Spacer()
                            TextField("0.00", value: $limitPrice, format: .number.precision(.fractionLength(2)))
                                .keyboardType(.decimalPad)
                                .multilineTextAlignment(.trailing)
                                .frame(width: 100)
                        }
                    }
                }

                Section {
                    Button(action: submit) {
                        HStack {
                            Spacer()
                            if submitting { ProgressView() }
                            else { Text("Place Order").bold() }
                            Spacer()
                        }
                    }
                    .disabled(submitting || (orderType == "LMT" && limitPrice <= 0))
                    .listRowBackground(action == "BUY" ? Color.green.opacity(0.18) : Color.red.opacity(0.18))
                }

                if let msg = resultMessage {
                    Section {
                        Text(msg)
                            .font(.caption)
                            .foregroundColor(resultIsError ? .red : .green)
                    }
                }
            }
            .navigationTitle("Order Ticket")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
            .onAppear {
                // Pre-fill the limit at the mid (or last/ask)
                if let bid = quote.bid, let ask = quote.ask {
                    limitPrice = ((bid + ask) / 2 * 100).rounded() / 100
                } else if let last = quote.last {
                    limitPrice = last
                } else if let ask = quote.ask {
                    limitPrice = ask
                }
            }
        }
    }

    private func submit() {
        submitting = true
        resultMessage = nil
        Task {
            defer { submitting = false }
            let req = OrderRequest(
                symbol: quote.symbol,
                expiry: Self.dateFmt.string(from: quote.expiry),
                strike: quote.strike,
                right: quote.right.rawValue,
                action: action,
                quantity: quantity,
                orderType: orderType,
                limitPrice: orderType == "LMT" ? limitPrice : nil
            )
            do {
                let res = try await api.placeOrder(req)
                resultIsError = false
                resultMessage = "Order \(res.orderId.map(String.init) ?? "?") submitted — status: \(res.status ?? "unknown")"
            } catch {
                resultIsError = true
                resultMessage = "Failed: \(error.localizedDescription)"
            }
        }
    }
}
