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
            Section {
                Text("The backend runs alongside IBKR TWS or IB Gateway and bridges market data to this device. See backend/README.md for setup.")
                    .font(.footnote)
                    .foregroundColor(.secondary)
            }
            Section("About") {
                LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")
                LabeledContent("Stack", value: "IBKR · FlashAlpha · Polygon")
            }
        }
        .navigationTitle("Settings")
    }
}
