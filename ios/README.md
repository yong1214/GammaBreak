# GammaBreak iOS

SwiftUI iPhone app for analyzing option Greeks and gamma walls served by the
GammaBreak backend.

## Generate the Xcode project

The repo ships with a `project.yml` instead of a fragile `.xcodeproj`. Use
[XcodeGen](https://github.com/yonaskolb/XcodeGen) to materialize it:

```bash
brew install xcodegen
cd ios
xcodegen generate
open GammaBreak.xcodeproj
```

## Configure the backend connection

On first launch open the **Settings** tab and set:

- **URL** — the backend base URL (e.g. `http://192.168.1.10:8000` on your LAN
  or `https://gammabreak.example.com` if deployed)
- **Bearer token** — must match `API_AUTH_TOKEN` in `backend/.env`

Add tickers from the **Watchlist** tab and tap one to open the analyzer.

## Screens

- **Watchlist** — managed list of tickers
- **Analyzer** — per-ticker prediction, IV rank header, multi-expiry gamma walls, and an option chain you can tap to open an order ticket
- **Positions** — live IBKR portfolio with mark-to-market P&L and account summary
- **Settings** — backend URL, bearer token, wall-crossing alert toggles
