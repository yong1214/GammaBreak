import SwiftUI

struct GammaCard: View {
    let profile: GammaProfile

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Gamma Profile").font(.headline)

            HStack(spacing: 16) {
                level("Call Wall", value: profile.callWall, color: .red)
                level("Zero Γ", value: profile.zeroGamma, color: .blue)
                level("Put Wall", value: profile.putWall, color: .green)
            }

            if let net = profile.netGex {
                HStack {
                    Text("Net GEX").font(.subheadline).foregroundColor(.secondary)
                    Spacer()
                    Text(formatGex(net))
                        .font(.subheadline.monospacedDigit())
                        .foregroundColor(net >= 0 ? .green : .red)
                }
            }

            if !profile.walls.isEmpty {
                Divider()
                ForEach(profile.walls.prefix(8)) { wall in
                    HStack {
                        Circle().fill(barColor(for: wall.type))
                            .frame(width: 8, height: 8)
                        Text(wall.strike, format: .currency(code: "USD"))
                            .font(.subheadline.monospacedDigit())
                        Text(wall.type.replacingOccurrences(of: "_", with: " "))
                            .font(.caption).foregroundColor(.secondary)
                        Spacer()
                        ProgressView(value: wall.strength)
                            .frame(width: 80)
                            .tint(barColor(for: wall.type))
                    }
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(12)
    }

    private func level(_ title: String, value: Double?, color: Color) -> some View {
        VStack {
            Text(title).font(.caption).foregroundColor(.secondary)
            if let v = value {
                Text(v, format: .currency(code: "USD"))
                    .font(.subheadline.monospacedDigit())
                    .foregroundColor(color)
            } else {
                Text("—").foregroundColor(.secondary)
            }
        }
        .frame(maxWidth: .infinity)
    }

    private func barColor(for type: String) -> Color {
        switch type {
        case "call_wall", "resistance": return .red
        case "put_wall", "support": return .green
        case "zero_gamma": return .blue
        default: return .gray
        }
    }

    private func formatGex(_ v: Double) -> String {
        let abs = Swift.abs(v)
        if abs >= 1e9 { return String(format: "%.2fB", v / 1e9) }
        if abs >= 1e6 { return String(format: "%.2fM", v / 1e6) }
        if abs >= 1e3 { return String(format: "%.2fK", v / 1e3) }
        return String(format: "%.0f", v)
    }
}
