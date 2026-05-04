import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var settings: AppSettings

    var body: some View {
        Form {
            Section("Backend") {
                TextField("URL", text: $settings.backendURL)
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                SecureField("Bearer token", text: $settings.authToken)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
            }

            Section("Alerts") {
                Toggle("Enable wall-crossing alerts", isOn: $settings.alertsEnabled)
                if settings.alertsEnabled {
                    HStack {
                        Text("Threshold")
                        Spacer()
                        Text(String(format: "%.2f%%", settings.alertThresholdPct))
                            .foregroundColor(.secondary)
                    }
                    Slider(value: $settings.alertThresholdPct, in: 0.05...2.0, step: 0.05)
                    Stepper("Poll every \(settings.alertPollMinutes) min",
                            value: $settings.alertPollMinutes, in: 1...60)
                    Text("Fires a local notification when spot is within the threshold of the call wall, put wall, or zero gamma. Same alert won't repeat within an hour.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Section {
                Text("The backend runs alongside IBKR TWS or IB Gateway and bridges market data to this device. See backend/README.md for setup.")
                    .font(.footnote)
                    .foregroundColor(.secondary)
            }

            Section("About") {
                LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")
                LabeledContent("Stack", value: "IBKR · Polygon · chain-derived GEX")
            }
        }
        .navigationTitle("Settings")
    }
}
