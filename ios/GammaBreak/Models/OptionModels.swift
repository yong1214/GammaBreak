import Foundation

struct Greeks: Codable, Hashable {
    let delta: Double?
    let gamma: Double?
    let theta: Double?
    let vega: Double?
    let rho: Double?
    let iv: Double?
}

enum OptionRight: String, Codable, Hashable {
    case call = "C"
    case put = "P"
}

struct OptionQuote: Codable, Hashable, Identifiable {
    var id: String { "\(symbol)-\(expiry)-\(strike)-\(right.rawValue)" }
    let symbol: String
    let expiry: Date
    let strike: Double
    let right: OptionRight
    let bid: Double?
    let ask: Double?
    let last: Double?
    let volume: Int?
    let openInterest: Int?
    let underlyingPrice: Double?
    let greeks: Greeks

    enum CodingKeys: String, CodingKey {
        case symbol, expiry, strike, right, bid, ask, last, volume, greeks
        case openInterest = "open_interest"
        case underlyingPrice = "underlying_price"
    }
}

struct OptionChain: Codable {
    let symbol: String
    let underlyingPrice: Double?
    let expiries: [Date]
    let quotes: [OptionQuote]

    enum CodingKeys: String, CodingKey {
        case symbol, expiries, quotes
        case underlyingPrice = "underlying_price"
    }
}

struct GammaWall: Codable, Hashable, Identifiable {
    var id: String { "\(strike)-\(type)" }
    let strike: Double
    let gammaExposure: Double
    let type: String
    let strength: Double

    enum CodingKeys: String, CodingKey {
        case strike, type, strength
        case gammaExposure = "gamma_exposure"
    }
}

struct GammaProfile: Codable {
    let symbol: String
    let spot: Double?
    let zeroGamma: Double?
    let callWall: Double?
    let putWall: Double?
    let walls: [GammaWall]
    let netGex: Double?

    enum CodingKeys: String, CodingKey {
        case symbol, spot, walls
        case zeroGamma = "zero_gamma"
        case callWall = "call_wall"
        case putWall = "put_wall"
        case netGex = "net_gex"
    }
}

struct PricePrediction: Codable {
    let symbol: String
    let spot: Double
    let horizonMinutes: Int
    let expectedMove: Double
    let upperTarget: Double
    let lowerTarget: Double
    let bias: String
    let confidence: Double
    let rationale: [String]

    enum CodingKeys: String, CodingKey {
        case symbol, spot, bias, confidence, rationale
        case horizonMinutes = "horizon_minutes"
        case expectedMove = "expected_move"
        case upperTarget = "upper_target"
        case lowerTarget = "lower_target"
    }
}

struct IVRank: Codable {
    let symbol: String
    let currentIv: Double?
    let rank: Double?
    let percentile: Double?
    let minIv: Double?
    let maxIv: Double?
    let samples: Int?
    let lookbackDays: Int?
    let message: String?

    enum CodingKeys: String, CodingKey {
        case symbol, rank, percentile, samples, message
        case currentIv = "current_iv"
        case minIv = "min_iv"
        case maxIv = "max_iv"
        case lookbackDays = "lookback_days"
    }
}

struct Position: Codable, Identifiable, Hashable {
    var id: String {
        "\(symbol)-\(secType)-\(expiry ?? "")-\(strike ?? 0)-\(right ?? "")"
    }
    let symbol: String
    let secType: String
    let right: String?
    let strike: Double?
    let expiry: String?
    let position: Double
    let avgCost: Double
    let marketPrice: Double?
    let marketValue: Double?
    let unrealizedPnl: Double?
    let realizedPnl: Double?

    enum CodingKeys: String, CodingKey {
        case symbol, position, expiry, right, strike
        case secType = "sec_type"
        case avgCost = "avg_cost"
        case marketPrice = "market_price"
        case marketValue = "market_value"
        case unrealizedPnl = "unrealized_pnl"
        case realizedPnl = "realized_pnl"
    }
}

struct AccountSummary: Codable {
    let netLiquidation: Double?
    let buyingPower: Double?
    let availableFunds: Double?
    let totalCashValue: Double?
    let grossPositionValue: Double?
    let maintMarginReq: Double?

    enum CodingKeys: String, CodingKey {
        case netLiquidation = "NetLiquidation"
        case buyingPower = "BuyingPower"
        case availableFunds = "AvailableFunds"
        case totalCashValue = "TotalCashValue"
        case grossPositionValue = "GrossPositionValue"
        case maintMarginReq = "MaintMarginReq"
    }
}

struct OrderRequest: Codable {
    let symbol: String
    let expiry: String         // yyyy-MM-dd
    let strike: Double
    let right: String          // "C" or "P"
    let action: String         // "BUY" or "SELL"
    let quantity: Int
    let orderType: String      // "LMT" or "MKT"
    let limitPrice: Double?

    enum CodingKeys: String, CodingKey {
        case symbol, expiry, strike, right, action, quantity
        case orderType = "order_type"
        case limitPrice = "limit_price"
    }
}

struct OrderResult: Codable {
    let orderId: Int?
    let permId: Int?
    let status: String?
    let filled: Double?
    let remaining: Double?
    let avgFillPrice: Double?

    enum CodingKeys: String, CodingKey {
        case orderId = "order_id"
        case permId = "perm_id"
        case status, filled, remaining
        case avgFillPrice = "avg_fill_price"
    }
}

struct WatchedSymbol: Codable, Hashable, Identifiable {
    var id: String { symbol }
    let symbol: String
    var alertCallWall: Bool
    var alertPutWall: Bool
    var alertZeroGamma: Bool

    static func defaultFor(_ symbol: String) -> WatchedSymbol {
        WatchedSymbol(symbol: symbol, alertCallWall: false, alertPutWall: false, alertZeroGamma: false)
    }
}
