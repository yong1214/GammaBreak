import SwiftUI

struct PredictionCard: View {
    let prediction: PricePrediction

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Prediction · \(prediction.horizonMinutes)m")
                    .font(.headline)
                Spacer()
                BiasBadge(bias: prediction.bias)
            }

            HStack(spacing: 24) {
                stat("Lower", value: prediction.lowerTarget, color: .red)
                stat("Spot", value: prediction.spot, color: .primary)
                stat("Upper", value: prediction.upperTarget, color: .green)
            }

            HStack {
                Label("±\(formattedMove)", systemImage: "arrow.up.and.down")
                Spacer()
                Label("\(Int(prediction.confidence * 100))% conf", systemImage: "gauge.medium")
            }
            .font(.subheadline.monospacedDigit())
            .foregroundColor(.secondary)

            if !prediction.rationale.isEmpty {
                Divider()
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(prediction.rationale, id: \.self) { line in
                        Label(line, systemImage: "circle.fill")
                            .font(.caption)
                            .labelStyle(BulletLabel())
                    }
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
    }

    private var formattedMove: String {
        String(format: "$%.2f", prediction.expectedMove)
    }

    private func stat(_ title: String, value: Double, color: Color) -> some View {
        VStack {
            Text(title).font(.caption).foregroundColor(.secondary)
            Text(value, format: .currency(code: "USD"))
                .font(.title3.monospacedDigit())
                .foregroundColor(color)
        }
        .frame(maxWidth: .infinity)
    }
}

private struct BulletLabel: LabelStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            configuration.icon.font(.system(size: 5)).foregroundColor(.accentColor)
            configuration.title
        }
    }
}

struct BiasBadge: View {
    let bias: String

    var body: some View {
        Text(bias.uppercased())
            .font(.caption.bold())
            .padding(.horizontal, 8).padding(.vertical, 4)
            .background(color.opacity(0.18))
            .foregroundColor(color)
            .cornerRadius(6)
    }

    private var color: Color {
        switch bias {
        case "bullish": return .green
        case "bearish": return .red
        case "pinned": return .blue
        default: return .gray
        }
    }
}
