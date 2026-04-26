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
